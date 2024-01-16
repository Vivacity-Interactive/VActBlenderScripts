import bpy, re

class _Settings:
    def __init__(self):
        self.force_name = True
        self.force_special_names = True
        self.clear_fixes = True

class VActSetupProject:
    class VActRule:
        def __init__(self, into="_Other", pre_fix="", post_fix="", regex_replace=None, regex_with=None, apply_before=True):
            self.into = into
            self.pre_fix = pre_fix
            self.post_fix = post_fix
            
            b_pattern = regex_replace and regex_with
            if b_pattern:
                self.pattern = re.compile(regex)
                self.regex_with = regex_with
            else: self.pattern = self.regex_with = None
            
            self.before = apply_before
        
        def apply(self, context, clear_fixes=False, apply_rename=True):
            if self.into:
                into = bpy.data.collections[self.into]
                
                for collection in context.users_collection:
                    collection.objects.unlink(context)
                    
                into.objects.link(context)
            
            if apply_rename: 
                if clear_fixes:
                    context.name = context.name.replace(pre_fix,"")
                    context.name = context.name.replace(post_fix,"")
                
                if self.pattern and self.before:
                    context.name = self.pattern.sub(self.regex_with, context.name)
                
                context.name = self.pre_fix + context.name + self.post_fix
                    
                if self.pattern and not self.before:
                    context.name = self.pattern.sub(self.regex_with, context.name)
            
            
    # 'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'HAIR', 'POINTCLOUD', 'VOLUME', 'GPENCIL', 'ARMATURE', 'LATTICE', 'EMPTY', 'LIGHT', 'LIGHT_PROBE', 'CAMERA', 'SPEAKER'
    _LUT_REFORM = dict([
        ('MESH', VActRule("Decor","SM_")),
        ('LIGHT', VActRule("Guides","L_")),
        ('CAMERA', VActRule("Guides","C_")),
        ('EMPTY', VActRule("Guides","E_")),
        ('ARMATURE', VActRule("SKEL","SKEL_")),
        ('ARMATURE_MESH', VActRule("Armature","SK_")),
        ('TEXTURE', VActRule(None,"T_")),
        ('MATERIAL', VActRule(None,"M_")),
        ('PARTICLE_SYSTEM', VActRule(None,"PS_"))
    ])
    
    _LUT_REFORM_SPECIAL = dict([
        ('LIGHT', "Key"),
        ('CAMERA', "Main")
    ])
    
                    
    def new_collection(self, name="",parent=None):
        _collection = bpy.data.collections.new(name)
        if parent:
            _parent = bpy.data.collections[parent]
            _parent.children.link(_collection)
        else:
            bpy.context.scene.collection.children.link(_collection)
        
    def do_execute(self, context, settings):
        
        for collection in context.collections:
            bpy.data.collections.remove(collection)
        
        self.new_collection("Guides")
        self.new_collection("Assets")
        self.new_collection("Models", "Assets")
        self.new_collection("Terrain", "Models")
        self.new_collection("Item", "Models")
        self.new_collection("Actor", "Models")
        self.new_collection("Decor", "Models")
        self.new_collection("Particle", "Models")
        self.new_collection("Volume", "Models")
        self.new_collection("Cloth", "Models")
        self.new_collection("Environment", "Models")
        self.new_collection("_Other", "Assets")
        self.new_collection("SKEL")
        self.new_collection("UCX")
        self.new_collection("LOD")
        self.new_collection("_Main")
        self.new_collection("_Decor","_Main")
        self.new_collection("_Particles","_Main")
        self.new_collection("_Terrain","_Main")
        self.new_collection("_Temp","_Main")
        
        _objects = []
        for object in context.objects:
            _objects.append(object)
                
        for object in _objects:
            rule = VActSetupProject._LUT_REFORM.get(object.type)
            if not rule: rule = VActSetupProject.VActRule()
            parent = object.parent
            if parent:
                sub_rule = VActSetupProject._LUT_REFORM.get(parent.type)
                _rule = VActSetupProject._LUT_REFORM.get(object.type + '_' + parent.type)
                rule = _rule if _rule else rule
            if settings.force_special_names:
                _name = VActSetupProject._LUT_REFORM_SPECIAL.get(object.type)
                if _name: object.name = _name
            
            rule.apply(object)
            print(object.name)
            
            if settings.force_name:
                object.data.name = object.name

settings = _Settings()

operator = VActSetupProject()
operator.do_execute(bpy.data, settings)