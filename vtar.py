import sys
import os
import struct
import argparse
import gzip
import tarfile


vmtar = struct.Struct(
    '<'
    '100s'      # [0]  0x000 name
    '8s'        # [1]  0x064 mode
    '8s'        # [2]  0x06C uid
    '8s'        # [3]  0x074 gid
    '12s'       # [4]  0x07C size
    '12s'       # [5]  0x088 mtime
    '8s'        # [6]  0x094 chksum
    'c'         # [7]  0x09C type
    '100s'      # [8]  0x09D linkname
    '6s'        # [9]  0x101 magic
    '2s'        # [10] 0x107 version
    '32s'       # [11] 0x109 uname
    '32s'       # [12] 0x129 gname
    '8s'        # [13] 0x149 devmajor
    '8s'        # [14] 0x151 devminor
    '151s'      # [15] 0x159 prefix
    'I'         # [16] 0x1F0 offset
    'I'         # [17] 0x1F4 textoffset
    'I'         # [18] 0x1F8 textsize
    'I'         # [19] 0x1FC numfixuppgs
)               #      0x200 (total size)

TAR_TYPE_FILE         = b'0'
TAR_TYPE_LINK         = b'1'
TAR_TYPE_SYMLINK      = b'2'
TAR_TYPE_CHARDEV      = b'3'
TAR_TYPE_BLOCKDEV     = b'4'
TAR_TYPE_DIR          = b'5'
TAR_TYPE_FIFO         = b'6'
TAR_TYPE_SHAREDFILE   = b'7'
TAR_TYPE_GNU_LONGLINK = b'K'
TAR_TYPE_GNU_LONGNAME = b'L'

GZIP_MAGIC = b'\037\213'

def parse_args():
    parser = argparse.ArgumentParser(description='Extracts and creates VMware ESXi .vtar files')
    parser.add_argument('vtarfile', help='.vtar file')
    parser.add_argument('-C', '--directory', metavar='DIR', help='Change to directory DIR')
    
    # Actions
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument('-x', '--extract', action='store_true', help='Extract contents of vtarfile')
    grp.add_argument('-c', '--create', action='store_true', help='Create a new vtarfile from directory')
    
    return parser.parse_args()


def main():
    args = parse_args()
    print(args)

    if args.create:
        if not args.directory:
            print("Error: Missing directory argument (-C DIR) for creating vtar.")
            sys.exit(1)
        create_vtar(args.directory, args.vtarfile)
    elif args.extract:
        extract_vtar(args.vtarfile, args.directory)




def create_header(path, rel_path, mode=TAR_TYPE_FILE, content_offset=None):
    stat = os.stat(path)
    size = stat.st_size if mode == TAR_TYPE_FILE else 0
    
    # Set UID, GID, uname, and gname according to the original archive
    uid = 311
    gid = 311
    uname = 'mts'
    gname = 'mts'
    
    # Set access mode according to the original archive
    mode_value = 0o444 if mode == TAR_TYPE_FILE else 0o755
    
    header = vmtar.pack(
        rel_path.encode('utf-8'),                                  # name
        '{:07o}\0'.format(mode_value).encode('utf-8'),             # mode
        '{:07o}\0'.format(uid).encode('utf-8'),                    # uid
        '{:07o}\0'.format(gid).encode('utf-8'),                    # gid
        '{:011o}\0'.format(size).encode('utf-8'),                  # size
        '{:011o}\0'.format(int(stat.st_mtime)).encode('utf-8'),    # mtime
        b'        ',                                               # chksum placeholder (8 bytes)
        mode,                                                      # type (already bytes)
        b'',                                                       # linkname
        b'visor ',                                                 # magic
        b' \x00',                                                  # version
        uname.encode('utf-8').ljust(32, b'\0'),                    # uname
        gname.encode('utf-8').ljust(32, b'\0'),                    # gname
        '{:07o}\0'.format(0).encode('utf-8'),                      # devmajor
        '{:07o}\0'.format(0).encode('utf-8'),                      # devminor
        b'',                                                       # prefix
        # 0,                                                       # offset (temporary placeholder)
        content_offset or 0,                                       # offset (temporary placeholder)
        0,                                                         # textoffset (temporary placeholder)
        0,                                                         # textsize (temporary placeholder)
        0                                                          # numfixuppgs
    )
    
    checksum = sum(header) & 0o777777
    chksum_str = '{:06o}\0 '.format(checksum).encode('utf-8')
    header = header[:148] + chksum_str + header[156:]

    return header, size




def create_vtar(directory, vtarfile):
    page_size = 4096

    with open(vtarfile, 'wb') as outfile:
        entries = []

        # Create entries for all directories and files in the directory
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                relpath = os.path.relpath(filepath, directory)

                # Create header for file
                header, file_size = create_header(filepath, relpath, mode=TAR_TYPE_FILE)
                entries.append((header, file_size, filepath, relpath))

            for subdir in os.listdir(dirpath):
                subpath = os.path.join(dirpath, subdir)
                if os.path.isdir(subpath):
                    relpath = os.path.relpath(subpath, directory) + '/'
                    header, _ = create_header(subpath, relpath, mode=TAR_TYPE_DIR)
                    entries.append((header, 0, subpath, relpath))

        # Write entries to the output file
        header_offset_dict = {}
        for i, header_data in enumerate(entries):
            header_offset = outfile.tell()
            print('header_offset / filepath', header_offset, filepath)

            header, file_size, filepath, relpath = header_data
            header += b'\0' * (512 - len(header))  # Align header to 512-byte boundary
            outfile.write(header)
            header_offset_dict[filepath] = header_offset
        print('header_offset_dict', header_offset_dict)

        # Write files content to the output file
        for header_data in entries:
            header, file_size, filepath, relpath = header_data

            if file_size > 0:  # This is a file entry
                # content_offset = outfile.tell()
                content_offset = round_up_to_multiple(outfile.tell(), 4096)
                outfile.seek(content_offset)
                print('content_offset', content_offset, filepath)

                # Write file content
                with open(filepath, 'rb') as infile:
                    infile_read = infile.read()
                    infile_read += b'\0' * (4096 - len(infile_read))  # Align header to 4096-byte boundary
                    outfile.write(infile_read)
                    
                end_offset = outfile.tell()

                # Update the header with correct offsets
                header_offset = header_offset_dict[filepath]
                print('header_offset', header_offset, filepath)
                outfile.seek(header_offset)  # Seek to offset field in the header
                header, file_size = create_header(filepath, relpath, mode=TAR_TYPE_FILE, content_offset=content_offset)
                header += b'\0' * (512 - len(header))  # Align header to 512-byte boundary
                outfile.write(header)   # Write offset
                outfile.seek(end_offset)        
            
        # Write the end-of-archive marker
        outfile.write(b'\0' * page_size)




def round_up_to_multiple(number, multiple):
    return ((number + multiple - 1) // multiple) * multiple



def extract_vtar(vtarfile, output_dir):
    with open(vtarfile, 'rb') as raw_input_file:
        gzip_header = raw_input_file.read(2)
        raw_input_file.seek(0)
        f = raw_input_file

        if gzip_header == GZIP_MAGIC:
            f = gzip.GzipFile(fileobj=raw_input_file)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            os.chdir(output_dir)
    
        print('pos         type offset   txtoff   txtsz    nfix size     name')
    
        while True:
            pos = f.tell()
            
            buf = f.read(vmtar.size)
            if len(buf) < vmtar.size:
                raise Exception('Short read at 0x{0:X}'.format(pos))
            
            obj = vmtar.unpack(buf)
            print('obj', obj)
            
            hdr_magic       = obj[9]
            if hdr_magic != b'visor ':
                break
            
            hdr_type        = obj[7]
            hdr_offset      = obj[16]
            hdr_textoffset  = obj[17]
            hdr_textsize    = obj[18]
            hdr_numfixuppgs = obj[19]
            hdr_size        = int(obj[4].rstrip(b'\0'), 8)
            hdr_name        = obj[0].rstrip(b'\0')
            
            print('0x{0:08X}  {1}    {2:08X} {3:08X} {4:08X} {5:04X} {6:08X} {7}'.format(
                pos, hdr_type.decode('utf-8'), hdr_offset, hdr_textoffset, hdr_textsize, hdr_numfixuppgs, hdr_size, hdr_name.decode('utf-8')))
                
            if hdr_type == TAR_TYPE_DIR:
                try:
                    os.mkdir(hdr_name.decode('utf-8'))
                except FileExistsError:
                    pass
            
            if hdr_type == TAR_TYPE_FILE:
                pos = f.tell()
                f.seek(hdr_offset, os.SEEK_SET)
                
                blob = f.read(hdr_size)
                with open(hdr_name.decode('utf-8'), 'wb') as outf:
                    outf.write(blob)
                
                f.seek(pos, os.SEEK_SET)


if __name__ == '__main__':
    sys.exit(main())