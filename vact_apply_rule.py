import bpy, re

class _Settings:
    def __init__(self):
        self.pre_fix = ""
        self.post_fix = "LOD0"
        self.regex_replace = None
        self.regex_with = None
        self.clear_fixes = True
        self.apply_before = True
        self.into_collection = "Decal"


class VActApllyRule:
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
    
    
    def do_execute(self, context, settings):
        rule = self.VActRule(
            settings.into_collection,
            settings.pre_fix,
            settings.post_fix,
            settings.regex_replace,
            settings.regex_with,
            settings.apply_before)
                 
        for object in context:
            rule.apply(object, settings.clear_fixes, settings.apply_before)
            

settings = _Settings()

layer = bpy.context.view_layer
active = layer.objects.active
selection = bpy.context.selected_objects

operator = VActApllyRule()
operator.do_execute(selection, settings)