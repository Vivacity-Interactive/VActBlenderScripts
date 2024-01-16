import bpy

class _Settings:
    def __init__(self):
        self.do_clear = False
        self.do_set = True
        

class _VActSetMeta:
    def do_generate(self, context, settings):
        for object in context:
            if settings.do_clear:
                object.vact_meta.clear()
            
            if settings.do_set:
                entry = object.vact_meta.add()
                entry.vact_icon = 'EVENT_S'
                entry.vact_type = 's'
                entry.vact_name = "entity"
                entry.vact_s = "Item"
                

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = _VActSetMeta()
operator.do_generate(selection, settings)