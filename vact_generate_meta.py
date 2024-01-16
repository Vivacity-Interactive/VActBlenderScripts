import bpy

class _Settings:
    def __init__(self):
        self.property_name = "entity"
        self.do_clear = True
        

class _VActGenerateMeta:
    def do_generate(self, context, settings):
        for object in context:
            if settings.do_clear:
                object.vact_meta.clear()
            
            for collection in object.users_collection:
                entry = object.vact_meta.add()
                entry.vact_icon = 'EVENT_S'
                entry.vact_type = 's'
                entry.vact_name = settings.property_name
                entry.vact_s = collection.name

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = _VActGenerateMeta()
operator.do_generate(selection, settings)