from typing import List, Tuple, Union


class Option:
    def __init__(self, name, description, subform=None):
        self.name = name
        self.description = description
        self.subform = subform

class FieldType:
    ...

class SubmitField(FieldType):
    def __init__(self, action: str):
        self.action = action

    def html(self, description, name, id_scope=None, name_scope=None):
        return f'<input type="submit" formaction="{self.action}" value="{description}">\n'
    
class TextField(FieldType):
    def __init__(self, default=None, hint=None):
        self.default = default
        self.hint = hint

    def html(self, description, name, id_scope=None, name_scope=None):
        eid = name
        if id_scope is not None:
            eid = id_scope + "." + eid
        if name_scope is not None:
            name = name_scope + "." + name

        label = f'<label for="{eid}">{description}: </label>'
        attr = f'type="text" name="{name}" id="{eid}"'
        if self.default is not None:
            attr += f' value="{self.default}"'
        if self.hint is not None:
            attr += f' placeholder="{self.hint}"'
        return label + f'<input {attr}>'

class OneOfField(FieldType):
    def __init__(self, options: List[Option]):
        self.options = options

    def html(self, description, name, id_scope=None, name_scope=None):
        eid = name
        if id_scope is not None:
            eid = id_scope + "." + eid
        if name_scope is not None:
            name = name_scope + "." + name
        
        s = '<fieldset>\n'
        s += f'<legend>{description}</legend>\n'
        for option in self.options:
            option_id = option.name
            if id_scope is not None:
                option_id = id_scope + "." + option_id
            s += f'<input type="radio" name="{name}" id="{option_id}" value={option.name}>'
            s += f'<label for="{option_id}"> {option.description} </label> <br>'

            option_name = option.name
            if name_scope is not None:
                option_name = name_scope + "." + option_name
            
            if option.subform is not None:
                s += f'<div style="margin-left:25px;">\n{option.subform.formulaic_html(option_id, option_name, True)}</div>\n'

        s += '</fieldset>\n'
        return s


    
class Field:
    def __init__(self, name, description, field_type, details=None):
        self.name = name
        self.description = description
        self.field_type = field_type
        self.details = details

    def html(self, id_scope):
        return self.field_type.html(self.description, self.name, id_scope)
        
        
def Formulaic(*fields):
    class F:
        formulaic_fields = fields
        
        @classmethod
        def formulaic_html(cls, id_scope=None, name_scope=None, embedded=False):
            s = ""
            for field in cls.formulaic_fields:
                s += field.html(id_scope)

            if not embedded:
                s = f'<form>\n{s}</form>\n'
            
            return s

        @classmethod
        def formulaic_construct(cls, response):
            breakpoint()

    return F



def formulaic(cls):
    if hasattr(cls, 'formulaic_fields'):
        return cls
    else:
        class F(cls, Formulaic()):
            ...
        return F

def field(name, description, field_type, details=None):
    f = Field(name, description, field_type, details)
    def decorator(cls):
        cls = formulaic(cls)
        cls.formulaic_fields = (f,) + cls.formulaic_fields
        return cls
    return decorator
