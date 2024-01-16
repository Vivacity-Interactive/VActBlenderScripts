import bpy, re

class _Settings:
    def __init__(self):
        self.batch_names = [
            ("spruce_half", "Spruce_Half"),
            ("Wooden_Sticks_And_Twigs_pdseq_lod3_Var5", "Spruce_Half_05"),
            ("Rounded_Cobble_Pack_umpncfdhw_lod3_Var3", "Cobble_03"),
            ("Rotten_Tree_Stump_wdzjdesbw_lod3_Var1", "Rotten_Tree_Stump_01"),
            ("Mossy_Forest_Boulder_wgoubaaaw_lod3", "Mossy_Forest_Boulder_02"),
            ("Mossy_Forest_Boulder_we2rbgvaw_lod3_Var1", "Mossy_Forest_Boulder_01"),
            ("Large_Fallen_Tree_wd3hfidbw_lod3_Var1", "Fallen_Tree_01"),
            ("Fallen_Spruce_Tree_tkerbglda_lod3", "Fallen_Spruce_01"),
            ("Beach_Boulder_weimcftga_lod3_Var1", "Beach_Boulder_01")
        ]
        self.regex_match = r'(S_|UCX_)?(%X%)(\d*)(.*)(LOD\w*)?'
        self.regex_replace = r'\1%X%\3\4\5'
        self.pre_regex = r'(spruce_half_\d*(_LOD\d*)?)'
        self.pre_replace = r'SM_\1'
        self.post_regex = r'^S_'
        self.post_replace = r'SM_'
        self.force_data_name = True


class VActBatchRename:
    def do_execute(self, context, settings):
        _post_regex = re.compile(settings.post_regex)
        _pre_regex = re.compile(settings.pre_regex)
        for pair in settings.batch_names:
            _regex = re.compile(settings.regex_match.replace("%X%", pair[0]))
            _replace = settings.regex_replace.replace("%X%", pair[1])
            
            for item in bpy.data.objects:
                _match = _regex.match(item.name)
                if _match:
                    name = item.name
                    pre_match = _pre_regex.match(name)                    
                    if pre_match:
                        name = _pre_regex.sub(settings.pre_replace, name)
                    name = _regex.sub(_replace, name)
                    name = _post_regex.sub(settings.post_replace, name)
                    print(name)
                    item.name = name
                    b_data = settings.force_data_name and item.data
                    if b_data: item.data.name = item.name


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActBatchRename()
operator.do_execute(selection, settings)