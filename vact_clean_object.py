import bpy, mathutils

class _Settings:
    def __init__(self):
        self.use_clear_transforms = True
        self.use_clear_vertex_groups = True
        self.use_clear_animations = True


class VActCleanObjects:
    def do_execute(self, context, settings):
        active = layer.objects.active
        bpy.ops.object.select_all(action='DESELECT')
            
        for object in context:
            layer.objects.active = object
            if settings.use_clear_transforms: object.matrix_world = mathutils.Matrix.Identity(4)
            if settings.use_clear_vertex_groups: object.vertex_groups.clear()
            if settings.use_clear_animations: object.animation_data_clear()
            for slot in object.material_slots:
                object.active_material_index = len(object.material_slots) - 1
                bpy.ops.object.material_slot_remove()
            object.modifiers.clear()
        
        layer.objects.active = active
        for selected in context: selected.select_set(True)
            

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActCleanObjects()
operator.do_execute(selection, settings)