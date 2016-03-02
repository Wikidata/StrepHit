$$('.cml_field.rando input').sort(function(a,b) {
   return Math.round(Math.random()*5) - 1 
}).each(function(o) { 
   o.getParent('.cml_row').inject(o.getParent('.cml_field')) 
})
