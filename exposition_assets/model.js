(function (root) {
  'use strict';
  const profiles = [
    {id:'A',position:'ST',age:22,x:4.4,y:1.0},
    {id:'B',position:'ST',age:28,x:3.2,y:2.5},
    {id:'C',position:'CM',age:24,x:1.4,y:4.2},
    {id:'D',position:'CB',age:31,x:-2.0,y:3.7},
    {id:'E',position:'GK',age:26,x:-4.3,y:1.3},
    {id:'F',position:'ST',age:19,x:4.0,y:-1.6},
    {id:'G',position:'CM',age:21,x:2.3,y:3.5},
    {id:'H',position:'CB',age:23,x:-3.5,y:-1.7},
    {id:'I',position:'GK',age:34,x:-1.0,y:-4.2},
    {id:'J',position:'ST',age:25,x:3.4,y:-3.0},
    {id:'K',position:'CM',age:29,x:0.5,y:-3.5},
    {id:'L',position:'CB',age:20,x:-3.1,y:3.0}
  ];
  function cosine(a,b) {
    const norm = Math.hypot(a.x,a.y)*Math.hypot(b.x,b.y);
    if (!norm) return null;
    return Math.max(-1,Math.min(1,(a.x*b.x+a.y*b.y)/norm));
  }
  function atAngle(degrees) {
    const radians = degrees*Math.PI/180;
    const similarity = Math.abs(Math.cos(radians))<1e-12 ? 0 : Math.cos(radians);
    return {x:Math.cos(radians),y:Math.sin(radians),similarity,distance:1-similarity};
  }
  function search(query, k, position='Todas', maxAge=40) {
    const eligible = profiles.filter(p=>(position==='Todas'||p.position===position)&&p.age<=maxAge);
    if (!Math.hypot(query.x,query.y)) return {eligible,results:[],error:'El vector de consulta no puede ser cero: mové X o Y.'};
    const ranked = eligible.map(p=>({...p,distance:1-cosine(query,p)}))
      .sort((a,b)=>a.distance-b.distance||a.id.localeCompare(b.id));
    return {eligible,results:ranked.slice(0,Math.max(0,k)),error:null};
  }
  // Grafo fijo y recorrido curado: ilustra navegación por capas, no construye un índice.
  const graph={
    nodes:[{id:'A',x:100},{id:'B',x:245},{id:'C',x:390},{id:'D',x:535},{id:'E',x:680},{id:'F',x:825}],
    layers:[['A','D'],['A','C','D','F'],['A','B','C','D','E','F']],
    edges:[[['A','D']],[['A','C'],['C','D'],['D','F']],[['A','B'],['B','C'],['C','D'],['D','E'],['E','F']]],
    query:705,
    steps:[
      {layer:0,current:'A',seen:['A'],candidates:['A'],text:'Entramos por A en la capa superior. La consulta Q está cerca de E, pero E todavía no aparece en esta capa.'},
      {layer:0,current:'D',seen:['A','D'],candidates:['D'],edge:['A','D'],text:'Comparamos el vecino D. Su distancia a Q es menor: avanzamos de A a D.'},
      {layer:1,current:'D',seen:['D'],candidates:['D'],text:'Descendemos conservando D como punto de entrada. La capa intermedia ofrece más conexiones.'},
      {layer:1,current:'F',seen:['D','C','F'],candidates:['F'],edge:['D','F'],text:'Desde D evaluamos C y F. F queda más cerca de Q y pasa a ser el candidato actual.'},
      {layer:2,current:'F',seen:['F'],candidates:['F'],text:'Descendemos a la capa base desde F. Aquí están todos los nodos.'},
      {layer:2,current:'E',seen:['F','E'],candidates:['E'],edge:['F','E'],text:'Exploramos E desde F. La distancia baja de 120 a 25 unidades: E mejora el candidato.'},
      {layer:2,current:'E',seen:['F','E','D'],candidates:['E'],text:'D no mejora a E. Terminamos este recorrido ilustrativo con E como vecino. HNSW real mantiene listas de candidatos y puede omitir vecinos.'}
    ]
  };
  function graphStep(index) {return graph.steps[Math.min(graph.steps.length-1,Math.max(0,index))];}
  const api={profiles,cosine,atAngle,search,graph,graphStep};
  if (typeof module!=='undefined'&&module.exports) module.exports=api;
  root.VectorLesson=api;
})(typeof globalThis!=='undefined'?globalThis:this);
