# ----------------------------------------------------------------------------
# cocos2d
# Copyright (c) 2008 Daniel Moisset, Ricardo Quesada, Rayentray Tappa, Lucio Torre
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright 
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of cocos2d nor the names of its
#     contributors may be used to endorse or promote products
#     derived from this software without specific prior written
#     permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ----------------------------------------------------------------------------
'''Grid data structure'''

__docformat__ = 'restructuredtext'

import pyglet
from pyglet import image
from pyglet.gl import *
from euclid import Point2, Point3

from director import director
import framegrabber

__all__ = ['GridBase',
           'Grid3D',
           'TiledGrid3D',
            ]

class GridBase(object):
    """
    A Scene that takes two scenes and makes a transition between them
    """
    texture = None
    
    def __init__(self):
        super(GridBase, self).__init__()
        self._active = False
        self.reuse_grid = 0     #! Number of times that this grid will be reused

    def init( self, grid ):
        '''Initializes the grid creating both a vertex_list for an independent-tiled grid
        and creating also a vertex_list_indexed for a "united" (non independent tile) grid.

        :Parameters:
            `grid` : euclid.Point2
                size of a 2D grid
        '''
 
        #: size of the grid. (rows, columns)
        self.grid = grid
        
        width, height = director.get_window_size()

        if self.texture is None:
            self.texture = image.Texture.create_for_size(
                    GL_TEXTURE_2D, width, 
                    height, GL_RGBA)
        
        self.grabber = framegrabber.TextureGrabber()
        self.grabber.grab(self.texture)

        #: x pixels between each vertex (float)
        self.x_step = width / self.grid.x
        #: y pixels between each vertex (float)
        self.y_step = height / self.grid.y

        
        #: tuple (x,y,z) that says where is the eye of the camera.
        #: used by ``gluLookAt()``
        self.camera_eye = Point3( width /2, height /2, self.get_z_eye() )
        #: tuple (x,y,z) that says where is pointing to the camera.
        #: used by ``gluLookAt()``
        self.camera_center = Point3( width /2, height /2, 0.0 )
        #: tuple (x,y,z) that says the up vector for the camera.
        #: used by ``gluLookAt()``
        self.camera_up = Point3( 0.0, 1.0, 0.0)

        self._init()

    def get_z_eye( self ):
        '''Returns the best distance for the camera for the current window size

        cocos2d uses a Filed Of View (fov) of 60
        '''
        width, height = director.get_window_size()
        eye_z = height / 1.1566
        return eye_z
        
    def before_draw( self ):
        # capture before drawing
        self.grabber.before_render(self.texture)


    def after_draw( self ):
        # capture after drawing
        self.grabber.after_render(self.texture)

        # blit
        glEnable(self.texture.target)
        glBindTexture(self.texture.target, self.texture.id)

        glPushAttrib(GL_COLOR_BUFFER_BIT)

        # go to 3D
        self._set_3d_projection()

        # center the image
        self._set_camera()

        self._blit()
        
        # go back to 2D
        self._set_2d_projection()
               
        glPopAttrib()
        glDisable(self.texture.target)

    def on_resize(self, w, h):
        '''on_resize handler. Don't return 'True' since this event
        shall be propagated to all the grids
        '''
        if not self.active:
            return
        
        self._set_3d_projection()
        
#        if director.window.width > self.texture.width or director.window.height > self.texture.height:
#            self.texture = image.Texture.create_for_size(
#                    GL_TEXTURE_2D, director.window.width, 
#                    director.window.height, GL_RGBA)
#            self.grabber = framegrabber.TextureGrabber()
#            self.grabber.grab(self.texture)
#        
#        txz = director._offset_x/float(self.texture.width)
#        tyz = director._offset_y/float(self.texture.height)
#        
#        rx = director.window.width - 2*director._offset_x
#        ry = director.window.height - 2*director._offset_y
#        
#        tx = float(rx)/self.texture.width+txz
#        ty = float(ry)/self.texture.height+tyz
#        
#        xsteps = (tx-txz) / self.grid.x
#        ysteps = (ty-tyz) / self.grid.y
#
#        self._on_resize( xsteps, ysteps, txz, tyz)


    def _set_active(self, bool):
        if self._active == bool:
            return
        self._active = bool
        if self._active == True:
            self._handlers = director.push_handlers(self.on_resize)
        elif self._active == False:
            self.vertex_list.delete()
            director.pop_handlers()
            director.set_2d_projection()
        else:
            raise Exception("Invalid value for GridBase.active")
                                        
    def _get_active(self):
        return self._active

    active = property(_get_active, _set_active,
                      doc='''Determines whether the grid is active or not                 
                     :type: bool
                     ''')       
    def _init(self):
        raise NotImplementedError('abstract')
        
    def _blit(self):
        raise NotImplementedError('abstract')

    def _on_resize(self):
        raise NotImplementedError('abstract')

    @classmethod
    def _set_3d_projection(cls):
        width, height = director.window.width, director.window.height

        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, 1.0*width/height, 0.1, 3000.0)
        glMatrixMode(GL_MODELVIEW)

    def _set_camera( self ):
        glLoadIdentity()
        gluLookAt( self.camera_eye.x, self.camera_eye.y, self.camera_eye.z,             # camera eye
                   self.camera_center.x, self.camera_center.y, self.camera_center.z,    # camera center
                   self.camera_up.x, self.camera_up.y, self.camera_up.z                 # camera up vector
                   )
  
    @classmethod
    def _set_2d_projection(cls):
        width, height = director.window.width, director.window.height
        width, height = director.get_window_size()
        glLoadIdentity()
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, 0, height, -100, 100)
        glMatrixMode(GL_MODELVIEW)
  

class Grid3D(GridBase):
    '''`Grid3D` is a 3D grid implementation. Each vertex has 3 dimensions: x,y,z
    
    The vindexed ertex array will be built with::

        self.vertex_list.vertices: x,y,z (floats)   
        self.vertex_list.tex_coords: x,y,z (floats)
        self.vertex_list.colors: RGBA, with values from 0 - 255
    '''

    def _init( self ):
        # calculate vertex, textures depending on screen size
        idx_pts, ver_pts_idx, tex_pts_idx = self._calculate_vertex_points()

        #: indexed vertex array that can be transformed.
        #: it has these attributes:
        #:
        #:    - vertices
        #:    - colors
        #:    - tex_coords
        #:
        #: for more information refer to pyglet's documentation: pyglet.graphics.vertex_list_indexed
        self.vertex_list = pyglet.graphics.vertex_list_indexed( (self.grid.x+1) * (self.grid.y+1), 
                            idx_pts, "t2f", "v3f/stream","c4B")
        
        #: original vertex array of the grid. (read-only)
        self.vertex_points = ver_pts_idx[:]
        self.vertex_list.vertices = ver_pts_idx
        self.vertex_list.tex_coords = tex_pts_idx
        self.vertex_list.colors = (255,255,255,255) * (self.grid.x+1) * (self.grid.y+1)
 
    def _blit(self ):
        self.vertex_list.draw(pyglet.gl.GL_TRIANGLES)

    def _calculate_vertex_points(self):        
        w = float(self.texture.width)
        h = float(self.texture.height)

        index_points = []
        vertex_points_idx = []
        texture_points_idx = []

        for x in xrange(0,self.grid.x+1):
            for y in xrange(0,self.grid.y+1):
                vertex_points_idx += [-1,-1,-1]
                texture_points_idx += [-1,-1]

        for x in xrange(0, self.grid.x):
            for y in xrange(0, self.grid.y):
                x1 = x * self.x_step 
                x2 = x1 + self.x_step
                y1 = y * self.y_step
                y2 = y1 + self.y_step
              
                #  d <-- c
                #        ^
                #        |
                #  a --> b 
                a = x * (self.grid.y+1) + y
                b = (x+1) * (self.grid.y+1) + y
                c = (x+1) * (self.grid.y+1) + (y+1)
                d = x * (self.grid.y+1) + (y+1)

                # 2 triangles: a-b-d, b-c-d
                index_points += [ a, b, d, b, c, d]    # triangles 

                l1 = ( a*3, b*3, c*3, d*3 )
                l2 = ( Point3(x1,y1,0), Point3(x2,y1,0), Point3(x2,y2,0), Point3(x1,y2,0) )

                #  building the vertex
                for i in xrange( len(l1) ):
                    vertex_points_idx[ l1[i] ] = l2[i].x
                    vertex_points_idx[ l1[i] + 1 ] = l2[i].y
                    vertex_points_idx[ l1[i] + 2 ] = l2[i].z

                # building the texels
                tex1 = ( a*2, b*2, c*2, d*2 )
                tex2 = ( Point2(x1,y1), Point2(x2,y1), Point2(x2,y2), Point2(x1,y2) )

                for i in xrange( len(tex1)):
                    texture_points_idx[ tex1[i] ] = tex2[i].x / w
                    texture_points_idx[ tex1[i] + 1 ] = tex2[i].y / h
 
        return ( index_points, vertex_points_idx, texture_points_idx )

class TiledGrid3D(GridBase):
    '''`TiledGrid3D` is a 3D grid implementation. It differs from `Grid3D` in that
    the tiles can be separated from the grid. 

    The vertex array will be built with::

        self.vertex_list.vertices: x,y,z (floats)   
        self.vertex_list.tex_coords: x,y (floats)
        self.vertex_list.colors: RGBA, with values from 0 - 255
    '''
    def _init( self ):
        # calculate vertex, textures depending on screen size
        ver_pts, tex_pts = self._calculate_vertex_points()

        #: vertex array that can be transformed.
        #: it has these attributes:
        #:
        #:    - vertices
        #:    - colors
        #:    - tex_coords
        #:
        #: for more information refer to pyglet's documentation: pyglet.graphics.vertex_list
        self.vertex_list = pyglet.graphics.vertex_list(self.grid.x * self.grid.y * 4,
                            "t2f", "v3f/stream","c4B")
        #: original vertex array of the grid. (read-only)
        self.vertex_points = ver_pts[:]
        self.vertex_list.vertices = ver_pts
        self.vertex_list.tex_coords = tex_pts
        self.vertex_list.colors = (255,255,255,255) * self.grid.x * self.grid.y * 4  

    def _blit(self ):
        self.vertex_list.draw(pyglet.gl.GL_QUADS)
        
    def _calculate_vertex_points(self):
        w = float(self.texture.width)
        h = float(self.texture.height)

        vertex_points = []
        texture_points = []

        for x in xrange(0, self.grid.x):
            for y in xrange(0, self.grid.y):
                x1 = x * self.x_step 
                x2 = x1 + self.x_step
                y1 = y * self.y_step
                y2 = y1 + self.y_step
              
                # Building the tiles' vertex and texture points
                vertex_points += [x1, y1, 0, x2, y1, 0, x2, y2, 0, x1, y2, 0 ]
                texture_points += [x1/w, y1/h, x2/w, y1/h, x2/w, y2/h, x1/w, y2/h]

        # Generates a quad for each tile, to perform tiles effect
        return (vertex_points, texture_points)
