import bpy, re, os, json

def _bone_intrp(type, targets, parms):
    return { 'type': type, 'parms': parms }

def _bone_entry(name, intrp, place, weight, deform):
    return { 'name': name, 'intrp': intrp, "place": place, 'weight': weight, 'deform': deform }

def _bone_entry_copy(entry, name = None):
    return { 'name': name or entry['name'], 'intrp': entry['intrp'], "place": entry['place'], 'weight': entry['weight'], 'deform': entry['deform'] }

class _NRVAct2UE:
    def __init__(self, condition = None):
        self.lot = {}
        self.regex = re.compile('^(ik_|cont_|ctrl_|dfh_|mch_|pole_|mark_|phys_)?(\D*)(\d*)(_r|_l)?')
        self._cond = condition
        self.map = { 'cont_': "CONTACT_", 'ctrl_': "CONTROL_", 'bone_': "" }
        
    def needed(self, name):
        return self._cond.test(name) if self._cond else 'UE' in name
    
    def use(self, name, b_deform = True):
        _match = self.regex.match(name);
        _name = None
        if _match:
            _prefix = _match.group(1) or ""
            _posfix = _match.group(4) or ""
            _title = _match.group(2) or ""
            _nr = _match.group(3) or ""
            _prefix = self.map.get(_prefix,_prefix)
            
            b_dfh = 'twist' in _title
            if b_dfh: _prefix = "DFH_"
            b_bone = not b_dfh and b_deform and not _prefix in {'ik_'}
            if b_bone: _prefix = "BONE_" + _prefix
            
            _name = _prefix.upper() + _title.title() + _nr + _posfix.upper()
        
        return _name


class _NRUE2VAct:
    def __init__(self, condition = None):
        self.lot = {}
        self.regex = re.compile('^(BONE_|CONTACT_|DFH_|CONTROL_|IK_|POLE_|MCH_|MARK_|PHYS_)?(\D*)(\d*)(_R|_L)?')
        self._cond = condition
        self.map = { 'BONE_': "", 'CONTACT_': "cont_", 'CONTROL_': "ctrl_" }
        
    def needed(self, name):
        return self._cond.test(name) if self._cond else 'VACT' in name
    
    def use(self, name, b_deform = True):
        _match = self.regex.match(name);
        _name = None
        if _match:
            _prefix = _match.group(1) or ""
            _posfix = _match.group(4) or ""
            _title = _match.group(2) or ""
            _nr = _match.group(3) or ""
            _prefix = self.map.get(_prefix,_prefix)
            
            b_no_prefix = b_com or 'Twist' in _title
            if b_no_prefix: _prefix = ""
            
            _name = _prefix.lower() + _title.lower() + _nr + _posfix.lower()
        
        return _name


class _SourceRig:
    def __init__(self, rig, skin):
        self._rig = rig
        self._skin = skin
        self.rig = None
        self.skin = None
        
    def resolve(context = bpy.data.objects):
        self.rig = context.get(self._rig)
        self.skin = context.get(self._skin)
        return self.rig, self.skin
        

class _Settings:
    def __init__(self):
        self.into = "_Converted"
        self.convert_bones = False
        self.convert_vertex_groups = True
        self.dump_base = False
        self.path = None
        self.indent = 1
        self.target_profile = None#'INTER_SKEL_Adult_VACT_Adjusted'
        self.source_profile = 'SKEL_Female_Adult_UE'
        self.source = _SourceRig('SKEL_Female_Adult_UE', 'SK_Female_Adult_UE')
        self.dump_regex_rules = [
            _NRVAct2UE(),
            _NRUE2VAct(),
        ]

class VActConvertRig:
    def do_execute(self, context, settings):
        into = bpy.data.collections[settings.into]
        base_dir = settings.path if settings.path else os.path.dirname(bpy.data.filepath)
        
        _tgt, _src = self._resolve_profile(settings.target_profile, settings.source_profile, base_dir, settings)
        
        #debug begin
        self._save_profile(_tgt, "_tgt_profile_rig_dbx", base_dir, settings)
        self._save_profile(_src, "_src_profile_rig_dbx", base_dir, settings)
        #debug end
        
        for rig in context:    
            b_mesh = rig.type in {'MESH'}
            if b_mesh:
                if (settings.convert_vertex_groups): self.do_convert_mesh(rig, _tgt, _src, settings)
            
            b_rig = not b_mesh and rig.type in {'ARMATURE'}
            if not b_rig: continue
        
            if (settings.dump_base): self.do_dump_base(rig, base_dir, settings)
            if (settings.convert_bones): self.do_convert_rig(rig, profile, into, settings)
    
    def do_convert_rig(self, context, tgt, src, into, settings): 
        for bone in context.data.bones:
            self.do_convert_bone(bone, tgt, src, into, settings)
            
    def do_convert_bone(self, context, tgt, src, into, settings):
        print(context.name)
    
    def do_convert_mesh(self, context, tgt, src, settings):
        for vertex_group in context.vertex_groups:
            self.do_convert_vertex_group(vertex_group, tgt, src, settings)
            
    def do_convert_vertex_group(self, context, tgt, src, settings):
        if context.name in src:
            _name = src[context.name][0]['name']
            print(context.name, '-->', _name)
            context.name = _name
    
    def do_dump_base(self, context, base_dir, settings):
        _bones = {}
        _rules = []
        for rule in settings.dump_regex_rules:
            if rule.needed(context.name): _rules.append(rule)
        
        for bone in context.data.bones:
            _name = None
            for rule in _rules:
                _name = rule.use(bone.basename, bone.use_deform)
                if _name: break
            _bones[bone.basename] = [_bone_entry(_name, None, None, 1.0, bone.use_deform)]
        
        self._save_profile(_bones, context.name, base_dir, settings)
    
    def _resolve_profile(self, tgt, src, base_dir, settings):
        _tgt = self._load_profile(tgt, base_dir, settings) if tgt else None
        _src = self._load_profile(src, base_dir, settings) if src else None
        
        if not _tgt: _tgt = self._inverse_profile(_src)
        if not _src: _src = self._inverse_profile(_tgt)
        
        return _tgt, _src
    
    def _save_profile(self, context, name, base_dir, settings):
        _data = json.dumps(context, indent=settings.indent, ensure_ascii=True)
        file_name = os.path.join(base_dir, bpy.path.clean_name(name))
        with open(file_name, 'w') as out_file: out_file.write(_data)
    
    def _load_profile(self, context, base_dir, settings):
        file_name = os.path.join(base_dir, context)
        with open(file_name, 'r') as in_file: data_file = json.load(in_file)
        return data_file
    
    def _inverse_profile(self, profile):
        _inv = {}
        for k, vl in profile.items():
            for v in vl:
                _k = v['name']
                if _k not in _inv: _inv[_k] = [ _bone_entry_copy(v, k) ]
                    
        return _inv


settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActConvertRig()
operator.do_execute(selection, settings)