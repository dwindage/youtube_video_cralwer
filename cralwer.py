#-*- coding: utf-8 -*-
import os
import sys
import urllib
import urllib2
import re
import json
import subprocess
import argparse

class Youtube:
    def __init__(self, url):
        self.video_id = self.__parse_url__(url)
        self.url = 'http://www.youtube.com/watch?v=' + self.video_id
        self.video_info_list = []
        self.audio_info_list = []

    def download(self, filename, verbose=False):
        if verbose: print 'video id : %s'%self.video_id
        if verbose: print '----------------------------------------------'

        self.__get_video_info__()
        if verbose: print 'video bitrate lists :', [str(x['bitrate']) for x in self.video_info_list][:3]
        if verbose: print 'video size lists :', [str(x['size']) for x in self.video_info_list][:3]
        if verbose: print 'audio bitrate lists :', [str(x['bitrate']) for x in self.audio_info_list][:3]
        # select always best bitrate video at 0
        video_info = self.video_info_list[0]
        audio_info = self.audio_info_list[0]
        if verbose: print 'selected video bitrate : %s'%video_info['bitrate']
        if verbose: print 'selected video size : %s'%video_info['size']
        if verbose: print 'selected audio bitrate : %s'%audio_info['bitrate']
        if verbose: print '----------------------------------------------'

        video_url = self.__build_download_url__(video_info)
        audio_url = self.__build_download_url__(audio_info)
        if verbose: print 'video download url : %s'%video_url
        if verbose: print 'audio download url : %s'%audio_url
        if verbose: print '----------------------------------------------'

        youtube.__download__(video_url, self.url, filename+'.video', verbose)
        youtube.__download__(audio_url, self.url, filename+'.audio', verbose)
        if verbose: print '----------------------------------------------'

        youtube.__merge__(filename, verbose)

        if verbose: print 'remove temporal file'
        os.remove(filename+'.video')
        os.remove(filename+'.audio')

        if verbose: print 'done'

    def __merge__(self, filename, verbose=False):
        if verbose: print 'merge %s and %s to %s'%(filename+'.video', filename+'.audio', filename)

        ffmpeg_command = ['ffmpeg',
                '-v', 'quiet',
                '-y',
                '-i', filename+'.video',
                '-i', filename+'.audio',
                '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental',
                filename]
        process = subprocess.Popen(' '.join(ffmpeg_command), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs = process.communicate()


    # http://www.youtube.com/watch?v=mV6cvBorTfg -> mV6cvBorTfg
    # http://youtu.be/mV6cvBorTfg -> mV6cvBorTfg
    # http://www.youtube.com/v/mV6cvBorTfg -> mV6cvBorTfg
    # mV6cvBorTfg -> mV6cvBorTfg
    def __parse_url__(self, url):
        data_list = url.split('/')[-1].split('?')[-1].split('&')

        if len(data_list) == 1 and not '=' in data_list[0]:
            return data_list[0]
        else :
            for data in data_list:
                if 'v=' in data:
                    key, value = data.split('=')
                    return value
        return url

    def __download__(self, url, referer='', filename='', verbose=False):
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17')
        if len(referer) > 0:
            req.add_header('Referer', referer)
        else:
            req.add_header('Referer', url)

        # if filename is empty then return entire data
        if len(filename) == 0:
            return urllib2.urlopen(req).read()

        stream = urllib2.urlopen(req)
        meta = stream.info()
        filesize = int(meta.getheaders('Content-Length')[0])
        if verbose: print 'downaloading : %s (Size : %s Bytes)'%(filename, '{:,.0f}'.format(float(filesize)))
        
        # save to file
        fp = open(filename, 'wb')

        filesize_dl = 0
        block_size = 8192
        while True:
            buffer = stream.read(block_size)
            if not buffer:
                break;
            filesize_dl += len(buffer)
            fp.write(buffer)

            status = r'%15s  [%3.2f%%]' % ('{:,.0f}'.format(filesize_dl), filesize_dl * 100. / filesize)
            status = status + chr(8)*(len(status)+1)
            if verbose: print status,
        
        fp.close()
        if verbose: print 'downloaded  : %s Bytes'%'{:,.0f}'.format(filesize)

    def __get_video_info__(self):
        html_data = self.__download__(self.url)

        # parsing
        re_get_player_script = re.compile('<script>var ytplayer = ytplayer \|\| {};ytplayer\.config = ([^*]*);\(function')
        player_scripts = re_get_player_script.findall(html_data)

        if not len(player_scripts) == 1:
            print >> sys.stderr, 'not found play info'
            exit(-1)

        video_info_list = []
        audio_info_list = []
        try:
            ytplayer_config_dict = json.loads( player_scripts[0] )
            ytplayer_config_list = urllib.unquote(ytplayer_config_dict['args']['adaptive_fmts']).split(',')

            for items in ytplayer_config_list:
                item_dict = {}
                for item in items.split('&'):
                    if not '=' in item:
                        continue
                    splited_list = item.split('=')
                    key = splited_list[0]
                    value = '='.join(splited_list[1:])
                    item_dict[key] = value
                if 'bitrate' in item_dict and 'video' in item_dict['type']:
                    video_info_list.append(item_dict)
                if 'bitrate' in item_dict and 'audio' in item_dict['type']:
                    audio_info_list.append(item_dict)
        except Exception, e:
            print >> sys.stderr, e
            exit(-1)
        
        # sort by bitrate
        self.video_info_list = sorted(video_info_list, key=lambda x: int(x['bitrate']), reverse=True)
        self.audio_info_list = sorted(audio_info_list, key=lambda x: int(x['bitrate']), reverse=True)

    def __build_download_url__(self, video_info):
        append_params = [video_info['url']]
        for key in video_info.keys():
            if key == 'url':
                continue
            append_params.append('%s=%s'%(key, video_info[key]))
        return '&'.join(append_params)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action="store_true")
    parser.add_argument('-o', '--output', help='output filename (default:video_id.mp4)', type=str, required=False, default='')
    parser.add_argument('youtube_url', help='input youtube url (ex:http://www.youtube.com/watch?v=mV6cvBorTfg)')

    args = parser.parse_args()
    youtube = Youtube(args.youtube_url)

    if len(args.output) == 0:
        args.output = youtube.video_id + '.mp4'
    youtube.download(filename=args.output, verbose=args.verbose)

