#!/usr/bin/env python3
import signal
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, GObject

import os
import sys
import time
import subprocess
import pwd
import argparse
from pathlib import Path
from threading import Thread
from PIL import Image, ImageDraw


def text_to_list(who_str):
    output = []
    line = ''
    for char in who_str:
        line += char
        if char == '\n':
            output.append(line)
            line = ''
    return output

USER = pwd.getpwuid(os.getuid()).pw_name
WDIR = '/tmp/qapplet_{}/'.format(USER)

def get_quota_for_user(username):
    po = os.popen('quota ' + username, 'r')
    quota_str = po.read()
    #print po
    #quota_str = '''Disk quotas for user ...
    # Filesystem  blocks   quota   limit   grace   files   quota   limit   grace
    #nfs460:/home  106636* 100000  120000    none    1760   10000   15000
    #'''
    
    quota_list = text_to_list(quota_str)[-1]
    quota_line = quota_list.strip().rstrip()
    quota_fields = quota_line.split(' ')
    quota_fields = [ f for f in quota_fields if f != '' ]
    field_offset = 0
    blocks = quota_fields[0+field_offset]
    user_quota = quota_fields[1+field_offset]

    if blocks.endswith('*'):
        blocks = blocks[:-1]

    blocks = int(blocks)
    user_quota = int(user_quota)

    return (blocks, user_quota,)


def show_notification(username, blocks, user_quota):
    help_str = "Try to close Firefox and delete .mozilla directory or contact your teacher.\n"
    del_mozilla = "Command: rm -r ~/.mozilla"
    blocks_m = blocks/1000
    user_quota_m = user_quota/1000
    info_str = "{0}: {1} MB/{2} MB\n".format(username, blocks_m, user_quota_m)
    info_str += help_str
    info_str += del_mozilla
    #print('Disk quota exceeded {}'.format(info_str))


def quota_info_str(username, blocks, user_quota):
    blocks_m = blocks//1000
    user_quota_m = user_quota//1000
    return 'Quota: {1}/{2} MB'.format(username, blocks_m, user_quota_m)


def draw_pie(percent, filename='pie.png'):
    N = 4
    
    if percent < 0.85:
        color = 'black'
    else:
        color = 'red'

    image = Image.new("RGBA", (128*N, 128*N), '#0000')
    draw = ImageDraw.Draw(image, image.mode)
    offset = 0*N
    draw.pieslice((offset, offset, (128-offset)*N, (128-offset)*N), -1-90, 360*percent-90, fill=color)

    del draw

    image = image.resize((20,20))
    image.save(filename, 'PNG')


def get_icon_filename(percent):
    if percent > 100:
        percent = 100

    icon_filename = os.path.join(WDIR, '{:03d}.png'.format(percent))
    return icon_filename


class Indicator():

    def __init__(self, username, check_interval):
        self.username = username
        self.check_interval = check_interval
        
        blocks, user_quota = get_quota_for_user(self.username)
        
        self.app = 'quota_applet'
        self.iconpath = get_icon_filename(int(100*blocks/user_quota))
        self.indicator = AppIndicator3.Indicator.new(
            self.app, self.iconpath,
            AppIndicator3.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)       
        self.indicator.set_menu(self.create_menu())
        
        #print(blocks/user_quota)
        
        self.indicator.set_label(quota_info_str(self.username, blocks, user_quota), self.app)
        
        # the thread:
        self.update = Thread(target=self.show_quota)
        # daemonize the thread to make the indicator stopable
        self.update.setDaemon(True)
        self.update.start()


    def about(self, source):
        subprocess.Popen(["baobab", Path.home()])


    def create_menu(self):
        menu = Gtk.Menu()
        # menu item 1
        item_1 = Gtk.MenuItem(label='Show disk usage')
        item_1.connect('activate', self.about)
        menu.append(item_1)
        # separator
        menu_sep = Gtk.SeparatorMenuItem()
        menu.append(menu_sep)
        # quit
        item_quit = Gtk.MenuItem(label='Quit')
        item_quit.connect('activate', self.stop)
        menu.append(item_quit)

        menu.show_all()
        return menu


    def show_quota(self):
        while True:
            time.sleep(self.check_interval)
    
            blocks, user_quota = get_quota_for_user(self.username)

            if blocks > user_quota:
                show_notification(self.username, blocks, user_quota)

            blocks_m = blocks//1000
            user_quota_m = user_quota//1000
            mention = 'Quota: {}/{} MB'.format(blocks_m, user_quota_m)

            #print(blocks/user_quota, blocks/user_quota)
            
            percent = int(100*blocks/user_quota)
            
            icon_filename = get_icon_filename(percent)
            
            # apply the interface update using  GObject.idle_add()
            
            #GObject.idle_add(
            #    self.indicator.set_icon,
            #    self.iconpath,
            #    priority=GObject.PRIORITY_DEFAULT
            #    )
            #self.indicator.set_icon_full(self.iconpath, 'ici')
            
            self.indicator.set_icon(icon_filename)

            GObject.idle_add(
                self.indicator.set_label,
                mention, self.app,
                priority=GObject.PRIORITY_DEFAULT
                )


    def stop(self, source):
        Gtk.main_quit()


def gen_pies():
    if not os.path.exists(WDIR):
        os.mkdir(WDIR)
    
    for i in range(0, 101):
        draw_pie(i/100, os.path.join(WDIR, '{:03d}.png'.format(i)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-interval', help='How often check the used disk space', default=15, type=int)

    args = parser.parse_args()

    gen_pies()
    
    os.environ['XAUTHORITY'] = os.path.join(Path.home(), '.Xauthority')

    Indicator(USER, **vars(args))
    Gtk.main()


if __name__ == "__main__":
    main()
