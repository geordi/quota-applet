#!/usr/bin/env python3
import signal
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, GObject, GLib

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from threading import Thread
from PIL import Image, ImageDraw


WDIR = os.path.join(os.getenv('XDG_CACHE_HOME'), 'qapplet')

class NoQuotaError(Exception):
    pass

def get_quota_for_user():
    output = subprocess.check_output(['quota', '-A'], text=True).splitlines()

    if output[0].endswith(': none'):
        raise NoQuota
    
    quota_fields = output[-1].strip().split(' ')
    quota_fields = [ f for f in quota_fields if f != '' ]
    blocks = quota_fields[0]
    user_quota = quota_fields[1]

    if blocks.endswith('*'):
        blocks = blocks[:-1]

    blocks = int(blocks)
    user_quota = int(user_quota)

    return (blocks, user_quota,)


def show_notification(blocks, user_quota):
    notified_path = os.path.join(WDIR, "notified")

    if os.path.exists(notified_path):
        return

    info = [
        "f{blocks//1000} MB/{user_quota//1000} MB",
        "Try to close Firefox and delete .mozilla directory or contact your teacher.",
        "Command: rm -r ~/.mozilla",

    ]
    subprocess.Popen(["notify-send", "-u", "critical", "Disk quota exceeded", "\n".join(info)])

    with open(notified_path, "w") as f:
        f.write("yes")


def quota_info_str(blocks, user_quota):
    blocks_m = blocks//1000
    user_quota_m = user_quota//1000
    return f'Quota: {blocks_m}/{user_quota_m} MB'


def draw_pie(percent, filename='pie.png'):
    N = 4
    
    if percent < 0.85:
        color = 'green'
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


class Indicator:

    def __init__(self, check_interval):
        self.check_interval = check_interval
        
        blocks, user_quota = get_quota_for_user()
        
        self.app = 'quota_applet'
        self.iconpath = get_icon_filename(int(100*blocks/user_quota))
        self.indicator = AppIndicator3.Indicator.new(
            self.app, self.iconpath,
            AppIndicator3.IndicatorCategory.OTHER)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)       
        self.indicator.set_menu(self.create_menu())
        
        #print(blocks/user_quota)
        
        self.indicator.set_label(quota_info_str(blocks, user_quota), self.app)
        
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
    
            blocks, user_quota = get_quota_for_user()

            if blocks > user_quota:
                show_notification(blocks, user_quota)

            blocks_m = blocks//1000
            user_quota_m = user_quota//1000
            mention = 'Quota: {}/{} MB'.format(blocks_m, user_quota_m)

            #print(blocks/user_quota, blocks/user_quota)
            
            percent = int(100*blocks/user_quota)
            
            icon_filename = get_icon_filename(percent)
            
            self.indicator.set_icon_full(icon_filename, f"{percent}%")

            GLib.idle_add(
                self.indicator.set_label,
                mention, self.app,
                priority=GLib.PRIORITY_DEFAULT
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

    try:
        get_quota_for_user()
    except NoQuotaError:
        print("No quota for this user, exiting the application")
        exit(0)

    gen_pies()
    Indicator(**vars(args))
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()


if __name__ == "__main__":
    main()
