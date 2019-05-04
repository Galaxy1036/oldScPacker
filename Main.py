# -*- coding: utf-8 -*-

import os
import sys
import lzma
import lzham
import hashlib
import argparse

from PIL import Image
from Reader import BinaryReader
from Writer import BinaryWriter


class Packer(BinaryWriter):

    def __init__(self, scFile, decompress, use_lzma, use_lzham, header, outputName):
        self.settings = {
                         'use_lzma': use_lzma,
                         'use_lzham': use_lzham,
                         'header': header,
                         'outputName': outputName
                         }

        if decompress:
            self.reader = BinaryReader(self.decompress(scFile))

        else:
            self.reader = BinaryReader(scFile)

        self.image_dict = {}
        super().__init__()

    def decompress(self, data):
        if data[:2] == b'SC':
            # Skip the header if there's any
            hash_length = int.from_bytes(data[6: 10], 'big')
            data = data[10 + hash_length:]

        if data[:4] == b'SCLZ':
            print('[*] Detected LZHAM compression !')

            dict_size = int.from_bytes(data[4:5], 'big')
            uncompressed_size = int.from_bytes(data[5:9], 'little')

            try:
                data = lzham.decompress(data[9:], uncompressed_size, {'dict_size_log2': dict_size})

            except Exception as exception:
                print('Decompression failed !')
                sys.exit()

        else:
            print('[*] Detected LZMA compression !')
            data = data[0:9] + (b'\x00' * 4) + data[9:]

            try:
                data = lzma.LZMADecompressor().decompress(data)

            except Exception as exception:
                print('Decompression failed !')
                sys.exit()

        print('[*] Decompression succeed !')

        return data

    def load_image(self, path):
        image = Image.open(path)
        self.image_dict[image.width, image.height] = image

    def pack(self):
        # ShapeCount etc...
        for i in range(6):
            self.write_uint16(self.reader.read_uint16())

        self.write(self.reader.read(5))  # 5 empty bytes

        exportCount = self.reader.read_uint16()
        self.write_uint16(exportCount)

        for i in range(exportCount):
            self.write_int16(self.reader.read_int16())  # ExportID

        for i in range(exportCount):
            self.write_string(self.reader.read_string())

        while self.reader.peek():
            dataBlockTag = self.reader.read(1).hex()
            dataBlockSize = self.reader.read_uint32()
            self.write_hexa(dataBlockTag)
            self.write_uint32(dataBlockSize)

            if dataBlockTag in ("18", "01"):
                if dataBlockSize > 5:
                    self.inject_texture()

                else:
                    self.write_uint8(self.reader.read_byte())  # PixelType
                    self.write_uint16(self.reader.read_uint16())  # Width
                    self.write_uint16(self.reader.read_uint16())  # Height

            else:
                self.write(self.reader.read(dataBlockSize))

        if self.settings['use_lzma'] or self.settings['use_lzham']:
            self.compress_data()

        with open(self.settings['outputName'], 'wb') as f:
            f.write(self.buffer)

    def inject_texture(self):
        pixelType = self.reader.read_byte()
        imageWidth = self.reader.read_uint16()
        imageHeight = self.reader.read_uint16()

        self.write_uint8(pixelType)
        self.write_uint16(imageWidth)
        self.write_uint16(imageHeight)

        image = self.image_dict.get((imageWidth, imageHeight))

        pixelSizeList = {
                         0: 4,
                         1: 4,
                         2: 2,
                         3: 2,
                         4: 2,
                         6: 2,
                         10: 1
                         }

        if image is not None:
            pixels = image.load()

            print('[INFO] Injecting texture, pixelFormat: {}, width: {}, height: {}'.format(pixelType, imageWidth, imageHeight))

            for y in range(image.height):
                for x in range(image.width):
                    colors = pixels[x, y]
                    self.write_pixel(pixelType, colors)

            self.reader.read(imageWidth * imageHeight * pixelSizeList[pixelType])

        else:
            self.write(self.reader.read(imageWidth * imageHeight * pixelSizeList[pixelType]))

    def write_pixel(self, pixelFormat, colors):
        red   = colors[0]
        green = colors[1]
        blue  = colors[2]
        alpha = colors[3]

        if pixelFormat == 0 or pixelFormat == 1:
            # RGBA8888
            self.write_uint8(red)
            self.write_uint8(green)
            self.write_uint8(blue)
            self.write_uint8(alpha)

        elif pixelFormat == 2:
            # RGBA8888 to RGBA4444
            r = (red >> 4) << 12
            g = (green >> 4) << 8
            b = (blue >> 4) << 4
            a = alpha >> 4

            self.write_uint16(a | b | g | r)

        elif pixelFormat == 3:
            # RGBA8888 to RGBA5551
            r = (red >> 3) << 11
            g = (green >> 3) << 6
            b = (blue >> 3) << 1
            a = alpha >> 7

            self.write_uint16(a | b | g | r)

        elif pixelFormat == 4:
            # RGBA8888 to RGBA565
            r = (red >> 3) << 11
            g = (green >> 2) << 5
            b = blue >> 3

            self.write_uint16(b | g | r)

        elif pixelFormat == 6:
            # RGBA8888 to LA88 (Luminance Alpha)
            self.write_uint8(alpha)
            self.write_uint8(red)

        elif pixelFormat == 10:
            # RGBA8888 to L8 (Luminance)
            self.write_uint8(red)

    def compress_data(self):
        if self.settings['use_lzma']:
            print('[*] Compressing .sc with lzma')

            filters = [
                       {
                        "id": lzma.FILTER_LZMA1,
                        "dict_size": 256 * 1024,
                        "lc": 3,
                        "lp": 0,
                        "pb": 2,
                        "mode": lzma.MODE_NORMAL
                        },
                       ]

            compressed = lzma.compress(self.buffer, format=lzma.FORMAT_ALONE, filters=filters)
            compressed = compressed[0:5] + len(self.buffer).to_bytes(4, 'little') + compressed[13:]

        else:
            print('[*] Compressing .sc with lzham')

            dict_size = 18

            compressed = lzham.compress(self.buffer, {'dict_size_log2': dict_size})
            compressed = 'SCLZ'.encode('utf-8') + dict_size.to_bytes(1, 'big') + len(self.buffer).to_bytes(4, 'little') + compressed

        fileMD5 = hashlib.md5(self.buffer).digest()

        # Flush the previous buffer
        self.buffer = b''

        if self.settings['header']:
            self.write('SC'.encode('utf-8'))
            self.write_uint32(1, 'big')
            self.write_uint32(len(fileMD5), 'big')
            self.write(fileMD5)

            print('[*] Header wrote !')

        self.write(compressed)

        print('[*] Compression done !')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='oldScPacker is a tool that allows you to insert PNG files into .sc files')
    parser.add_argument('files', help='PNG files to inject into .sc', nargs='+')
    parser.add_argument('-lzma', '--lzma', help='Compress the output .sc with LZMA', action='store_true')
    parser.add_argument('-lzham', '--lzham', help='Compress the output .sc with LZHAM', action='store_true')
    parser.add_argument('-header', '--header', help='add SC header to the beginning of the compressed .sc', action='store_true')
    parser.add_argument('-d', '--decompress', help='decompress your .sc before injecting PNG into it', action='store_true')
    parser.add_argument('-o', '--outputname', help='define an output name for the .sc file (if not specified the output filename is set to <scfilename> + _packed.sc')
    parser.add_argument('-sc', '--scfile', help='.sc where PNG should be injected', required=True)

    args = parser.parse_args()

    if args.scfile.endswith('.sc') and not args.scfile.endswith('tex.sc'):
        if not (args.lzma and args.lzham):
            if os.path.isfile(args.scfile):
                with open(args.scfile, 'rb') as f:
                    if args.outputname:
                        output_name = args.outputname

                    else:
                        output_name = '_packed'.join(os.path.splitext(args.scfile))

                    scPacker = Packer(f.read(), args.decompress, args.lzma, args.lzham, args.header, output_name)

                for file in args.files:
                    if file.endswith('.png'):
                        if os.path.isfile(file):
                            scPacker.load_image(file)

                        else:
                            print('[*] {} don\'t exists'.format(file))
                            sys.exit()

                    else:
                        print('[*] Only .png files are supported !')
                        sys.exit()

                scPacker.pack()

            else:
                print('[*] {} don\'t exists'.format(args.scfile))

        else:
            print('[*] You cannot set both lzma and lzham compression !')

    else:
        print('[*] Only .sc files are supported (not _tex.sc) !')
