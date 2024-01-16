import bpy, re, bmesh

class _Settings:
    def __init__(self):
        self.batch_names = [
            ("spruce_half", "Spruce_Half"),
            ("Wooden_Sticks_And_Twigs_pdseq_lod3_Var5", "Twigs_05"),
            ("Rounded_Cobble_Pack_umpncfdhw_lod3_Var3", "Cobble_03"),
            ("Rotten_Tree_Stump_wdzjdesbw_lod3_Var1", "Rotten_Tree_Stump_01"),
            ("Mossy_Forest_Boulder_wgoubaaaw_lod3", "Mossy_Forest_Boulder_02"),
            ("Mossy_Forest_Boulder_we2rbgvaw_lod3_Var1", "Mossy_Forest_Boulder_01"),
            ("Large_Fallen_Tree_wd3hfidbw_lod3_Var1", "Fallen_Tree_01"),
            ("Fallen_Spruce_Tree_tkerbglda_lod3", "Fallen_Spruce_01"),
            ("Beach_Boulder_weimcftga_lod3_Var1", "Beach_Boulder_01"),
            ("Huge_Icelandic_Lava_Cliff_siEoZ_lod3", "Huge_Icelandic_Cliff_01"),
            ("Icelandic_Rock_Plates_taerZ_lod3", "Icelandic_Rock_Plates_01"),
        ]
        self.regex_match = r'(S_|UCX_)?(%X%)(\d*)(.*)(LOD\w*)?'
        self.regex_replace = r'\1%X%\3\4\5'
        self.post_regex = r'^S_'
        self.post_replace = r'SM_'
        self.from_collection = '_Import'


class VActBatchReplace:
    def do_execute(self, context, settings):
        _collection = bpy.data.collections.get(settings.from_collection) if settings.from_collection else None
        _post_regex = re.compile(settings.post_regex)
        items = _collection.objects if _collection else bpy.data.objects
        for pair in settings.batch_names:
            _regex = re.compile(settings.regex_match.replace("%X%", pair[0]))
            _replace = settings.regex_replace.replace("%X%", pair[1])
            target_name = _post_regex.sub(settings.post_replace, _replace)
            for item in items:
                _match = _regex.match(item.name)
                if _match:
                    target_name = _regex.sub(_replace, item.name)
                    target = bpy.data.objects.get(target_name)
                    if target:
                        #base = bmesh.from_edit_mesh(item.data)
                        #base.update_edit_mesh(target.data)
                        for layer in target.data.uv_layers:
                            _layer = item.data.uv_layers.get(layer.name)
                            if _layer:
                                print(item.name, layer.name)#item.data.uv_layers[layer.name] = layer

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActBatchReplace()
operator.do_execute(selection, settings)