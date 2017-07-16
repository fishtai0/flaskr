"""
GitHub-style identicons as SVGs in Python.

Inspired by https://github.com/stewartlord/identicon.js

Author: Yuwei Tian
Email: fishtai0[at]outlook.com

Copyright (C) 2017  Yuwei Tian  https://github.com/fishtai0

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import math
import colorsys


IDENTICON_DEFAULTS = {
    'background': [240, 240, 240, 255],
    'margin': 0.08,
    'size': 64,
    'grid_size': 5,
    'saturation': 0.7,
    'brightness': 0.5,
}


class IdenticonSVG:
    def __init__(self, hash, **options):
        if not isinstance(hash, str) or len(hash) < 15:
            raise ValueError('A hash of at least 15 characters is required.')

        self.hash = hash
        self.options = IDENTICON_DEFAULTS
        if isinstance(options, dict):
            self.options.update(options)

        self.size = self.options['size']
        self.grid_size = self.options['grid_size']
        base_margin = math.floor(self.size * self.options['margin'])
        # cell size
        self.cell = math.floor((self.size - base_margin * 2) / self.grid_size)
        # real margin
        self.margin = math.floor((self.size - self.cell * self.grid_size) / 2)

        self.background = self.options['background']
        self.saturation = self.options['saturation']
        self.brightness = self.options['brightness']

        if 'foreground' in self.options:
            self.foreground = self.options['foreground']
        else:
            # foreground defaults to last 6 chars as hue at 70% saturation,
            # 50% brightness
            hue = int(hash[-6:], 16) / 0xffffff
            self.foreground = [int(c * 255)
                               for c in self.hsl2rgb(hue,
                                                     self.saturation,
                                                     self.brightness)]

    def image(self):
        return Svg(self.size, self.foreground, self.background)

    def draw_1(self, bg, fg, image):
        # the first 15 characters of the hash control the pixels (even/odd)
        # they are drawn down the middle first, then mirrored outwards
        for i in range(self.grid_size * (self.grid_size + 1) // 2):
            color = bg if int(self.hash[i], 16) & 1 else fg
            if i < 5:
                # <-|->
                self.rectangle(2 * self.cell + self.margin,
                               i * self.cell + self.margin,
                               self.cell, self.cell, color, image)
            elif i < 10:  # <-|||->
                self.rectangle(1 * self.cell + self.margin,
                               (i - 5) * self.cell + self.margin,
                               self.cell, self.cell, color, image)
                self.rectangle(3 * self.cell + self.margin,
                               (i - 5) * self.cell + self.margin,
                               self.cell, self.cell, color, image)
            else:  # |||||
                self.rectangle(0 * self.cell + self.margin,
                               (i - 10) * self.cell + self.margin,
                               self.cell, self.cell, color, image)
                self.rectangle(4 * self.cell + self.margin,
                               (i - 10) * self.cell + self.margin,
                               self.cell, self.cell, color, image)

    def draw_2(self, fg, image):
        self.hash = int(self.hash, 16)
        self.hash >>= 24
        square_x = square_y = 0
        for i in range(self.grid_size * (self.grid_size + 1) // 2):
            if self.hash & 1:
                x = self.margin + square_x * self.cell
                y = self.margin + square_y * self.cell
                self.rectangle(x, y, self.cell, self.cell, fg, image)
                x = self.margin + (self.grid_size - 1 - square_x) * self.cell
                self.rectangle(x, y, self.cell, self.cell, fg, image)
            self.hash >>= 1  # shift to right
            square_y += 1
            if square_y == self.grid_size:
                square_y = 0
                square_x += 1

    def render(self):
        image = self.image()
        # bg = image.color(*self.background)
        fg = image.color(*self.foreground)
        # self.draw_1(bg, fg, image)
        self.draw_2(fg, image)
        return image

    def rectangle(self, x, y, w, h, color, image):
        image.rectangles.append({
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'color': color
        })

    @staticmethod
    def hsl2rgb(h, s, b):
        return colorsys.hls_to_rgb(h, s, b)

    def to_string(self, raw=False):
        if raw:
            return self.render().get_dump()

        return self.render().get_base64()


class Svg:
    def __init__(self, size, foreground, background, rectangles=None):
        self.size = size
        self.foreground = self.color(*foreground)
        self.background = self.color(*background)
        if not rectangles:
            rectangles = []
        self.rectangles = rectangles

    def color(self, r, g, b, a=256):
        values = [round(c) for c in [r, g, b]]
        values.append(a / 255 if a >= 0 and a <= 255 else 1)
        return 'rgba({0}, {1}, {2}, {3})'.format(*values)

    def get_dump(self):
        stroke = self.size * 0.005
        xml = ("<svg xmlns='http://www.w3.org/2000/svg' "
               "width='{0}' height='{0}' style='background-color:{1};'>"
               "<g style='fill:{2}; stroke:{2}; stroke-width:{3};'>").format(
                   self.size, self.background, self.foreground, stroke)
        for i in range(len(self.rectangles)):
            rect = self.rectangles[i]
            if rect['color'] == self.background:
                continue
            xml += ("<rect x='{0[x]}' y='{0[y]}' "
                    "width='{0[w]}' height='{0[h]}'/>").format(rect)
        xml += '</g></svg>'
        return xml

    def get_base64(self):
        from base64 import b64encode
        return b64encode(self.get_dump().encode('utf-8')).decode('utf-8')


def main():
    from hashlib import md5
    str_ = 'stewartlord'
    hash = md5(str_.encode('utf-8')).hexdigest()
    return IdenticonSVG(hash, size=420, grid_size=9).to_string()


if __name__ == '__main__':
    data = main()
    print(('<img width="420" height="420" '
           'src="data:image/svg+xml;base64,{0}">').format(data))
