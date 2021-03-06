## oldScPacker
**oldScPacker** is a python script that allows you to inject PNG files into .sc files, **.sc** files are specific files used by **Supercell** in their own game engine.

### How to use it ?
The basic usage to inject one PNG is:  

> python Main.py <png\_file\> -sc <sc_file\>

Example:  

> python Main.py ui\_spell\_hunter.png -sc ui\_spell\_hunter.sc 

----------

However if you want to inject multiple png use:  

> python Main.py <png\_file1\> <png\_file2\> ... -sc <sc\_file>

Example:  

> python Main.py chr\_magic\_archer\_dl\.png  chr\_magic\_archer\_dl\_.png -sc chr\_magic\_archer\_dl.sc


### Options
**oldScPacker** can also takes few optionals arguments which are:  

* `-lzma`: if this argument is specified .sc file will be compressed using lzma
* `-lzham`: if this argument is specified .sc file will be compressed using lzham
* `-header`: add Supercell header at the beginning of the compressed .sc file
* `-o`: optionnal output filename for the .sc file, if this argument isn't specified .sc file will be saved as <sc\_filename\> + _packed.sc 
* `-d`: decompress the .sc file before injecting PNG

Command Example:
> python Main.py chr\_magic\_archer\_dl\.png  chr\_magic\_archer\_dl\_.png -sc chr\_magic\_archer\_dl.sc -d -lzma -header -o afilename.sc

### Dependencies
To install **oldScPacker** dependencies run the following command 
 
> python -m pip install -r requirements.txt
