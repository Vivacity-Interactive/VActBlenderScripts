import bpy

class _Settings:
    def __init__(self):
        self.into = "Decor"

class VActExtractUniqueAsset:
    def do_execute(self, context, settings):
        uniqe = dict();
        into = bpy.data.collections[settings.into]
        
        for item in context:
            name = item.data.name
            if name not in uniqe: uniqe[name] = item
        
        for _, item in uniqe.items():
            asset = item.copy()
            asset.name = item.data.name
            
            for collection in asset.users_collection:
                collection.objects.unlink(asset)
            
            into.objects.link(asset)
            


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActExtractUniqueAsset()
operator.do_execute(selection, settings)