Cocograph v0.2.0 tile map editor for cocos2d
requires: python 2.5+, pyglet 1.1+
included: cocos2d, and kytten (could become dependencies later)


How to use

'Open' or create a 'New' map. Tilesets required by an existing map will 
be loaded with the map. Click on a tile to select it for use with the 
pencil tool. Click on a tileset name tab to use that tileset.


Creating a New Map

Enter the size of tiles and the map and submit, you can then save the 
map and it will be loaded into Cocograph. You can then open an existing
tileset from the tileset dialog menu or create a new one.


Creating a New Tileset

From Dir:
Select a directory containing images (.png, ,jpg, .bmp, .gif), you 
can then save the tileset and it will be loaded into Cocograph. You
will probably want the images in the directory to be the same size.

From Image:
Select and image, enter the tile size and if there's any padding
around the tiles. You can then save the tileset and it will be loaded 
into Cocograph.


Layers

The 'op' slider adjusts the opacity of the currently selected layer.
'+' adds a new layer.  Enter a layer ID, tile size, and Z origin
(to determine the ordering of layers). '-' removes the currently 
selected layer. 'Properties' allows you to add / change properties
for the currently selected layer.


Tools

TOOL    LEFT CLICK ACTION               RIGHT CLICK ACTION
pencil  draw selected tile from tileset select clicked map tile (picker)
picker  select clicked map tile         select clicked map tile
eraser  set clicked map tile to None    set clicked map tile to None
move    click and drag around the map   click and drag around the map
zoom    zoom in                         zoom out


Keyboard Shortcuts

KEY+MODIFIER                    ACTION
ctrl+click on tile or cell      edit properties
spacebar down                   click and drag around the map (move)
ctrl+s                          save map
ctrl+=                          zoom in
ctrl+-                          zoom out
mouse scroll wheel              zoom
ctrl+d                          debug info toggle
ctrl+q                          quit
ctrl+s                          save

Commandline Usage: run_cocograph.py <level.xml> to open a level
or simply run or double click run_cocograph.py and then open or create
a new map.


LICENSE:

Copyright (c) 2009, Devon Scott-Tunkin
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <copyright holder> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Thanks to Richard Jones for his original editor and great tile library
and Conrad Wong for the wonderful "kytten" gui library

