# VMware VTAR Utility

A utility for archiving and extracting VMware .vtar files

## Features

*   **Create \`.vtar\` archives**: Package files and directories into VMware \`.vtar\` format.
*   **Extract \`.vtar\` archives**: Unpack contents of VMware \`.vtar\` files.

## Installation

To use this tool, you need Python 3.6 or higher. You can clone this repository and run the script directly:

```
git clone https://github.com/ForceFledgling/vmware-vtar-tool.git
cd vmware-vtar-util
```

## Usage

### **Creating a** `**.vtar**` **Archive**

To create a `.vtar` archive from a directory:

```
python vtar.py -c -C /path/to/directory output.vtar
```

*   `-c, --create` – Create a new `.vtar` archive.
*   `-C DIR` – Directory to archive.
*   `output.vtar` – The output `.vtar` file.

### **Extracting a** `**.vtar**` **Archive**

To extract a `.vtar` archive to a directory:

```
python vtar.py -x -C /path/to/extract_dir input.vtar
```

*   `-x, --extract` – Extract contents of the `.vtar` file.
*   `-C DIR` – Directory to extract files into.
*   `input.vtar` – The `.vtar` file to extract.

## Details

The `.vtar` format used by this utility is specific to VMware ESXi and contains various file types such as directories and files, with metadata about each entry.

## Header Structure

The utility uses a custom header format for `.vtar` files, including fields like name, mode, size, and timestamps.

## Example

```
# Create a .vtar archive
python vtar.py -c -C /path/to/directory output.vtar

# Extract a .vtar archive
python vtar.py -x -C /path/to/extract_dir input.vtar
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you have improvements or bug fixes.

## License

This project is licensed under the MIT License.

## Notes

*   Ensure the directory paths and `.vtar` file names are correct before running commands.
*   The `.vtar` format may include special handling for VMware environments and may not be compatible with standard tar utilities.