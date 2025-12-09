import bpy, mathutils, math

class _Cursor:
    class Bound:
        def __init__(self):
            self.min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
            self.max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
            self.size = mathutils.Vector((float(0), float(0), float(0)))
            self.eq = mathutils.Vector((float(1), float(1), float(1)))
        
        def union(self, vec):
            self.min.x = min(self.min.x, vec[0])
            self.min.y = min(self.min.y, vec[1])
            self.min.z = min(self.min.z, vec[2])
            self.max.x = max(self.max.x, vec[0])
            self.max.y = max(self.max.y, vec[1])
            self.max.z = max(self.max.z, vec[2])
            
        def eval(self):
            self.size = self.max - self.min
            self.eq = mathutils.Vector((self.max.x == self.min.x, self.max.y == self.min.y, self.max.z == self.min.z))
            
    def __init__(self):
        pass

class _Settings:
    def __init__(self):
        self.padding = (0.1,0.1,0.1)

class VActResetTransform:
    def do_execute(self, context, settings):
        _len = len(context)
        
        PADD = mathutils.Vector(settings.padding)
        N = mathutils.Vector((float(_len), float(_len), float(_len)))
        
        bound = _Cursor.Bound()
        for item in context:
            for vec in item.bound_box:
                bound.union(vec)
        
        bound.eval()
        UNIT = bound.size + PADD
        _dim = int(math.sqrt(_len))
        
        for index, item in enumerate(context):
            INDEX = mathutils.Vector((index % _dim, int(index / _dim), 0))
            item.location = INDEX * UNIT
            
settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActResetTransform()
operator.do_execute(selection, settings)