const test=require('node:test');
const assert=require('node:assert/strict');
const M=require('../exposition_assets/model.js');

test('coseno y distancia en 0, 90 y 180 grados',()=>{
  for(const [angle,similarity,distance] of [[0,1,0],[90,0,1],[180,-1,2]]){
    const state=M.atAngle(angle);
    assert.ok(Math.abs(state.similarity-similarity)<1e-12);
    assert.ok(Math.abs(state.distance-distance)<1e-12);
  }
});
test('top-k aplica restricciones antes del ranking y ordena cosenos',()=>{
  const {eligible,results}=M.search({x:4,y:1},3,'ST',25);
  assert.equal(eligible.length,3);
  assert.deepEqual(results.map(p=>p.id),['A','F','J']);
  assert.ok(results.every(p=>p.age<=25&&p.position==='ST'));
  assert.ok(results.every((p,i)=>i===0||results[i-1].distance<=p.distance));
});
test('cero candidatos, menos de k y vector nulo',()=>{
  assert.equal(M.search({x:4,y:1},5,'GK',18).results.length,0);
  assert.equal(M.search({x:4,y:1},8,'GK',30).results.length,1);
  assert.ok(M.search({x:0,y:0},3).error);
  assert.equal(M.cosine({x:0,y:0},{x:1,y:0}),null);
});
test('top-k coincide con cálculo independiente en consultas y filtros',()=>{
  for(const x of [-5,-1,0,3,5])for(const y of [-4,0,2,5]){
    if(!x&&!y)continue;
    for(const pos of ['Todas','ST','CM','CB','GK']){
      const expected=M.profiles.filter(p=>(pos==='Todas'||p.position===pos)&&p.age<=25)
        .map(p=>({id:p.id,d:1-(x*p.x+y*p.y)/(Math.hypot(x,y)*Math.hypot(p.x,p.y))}))
        .sort((a,b)=>a.d-b.d||a.id.localeCompare(b.id)).slice(0,4).map(p=>p.id);
      assert.deepEqual(M.search({x,y},4,pos,25).results.map(p=>p.id),expected);
    }
  }
});
test('recorrido HNSW determinista, aristas válidas y descensos coherentes',()=>{
  assert.equal(M.graphStep(-1).current,'A');
  assert.equal(M.graphStep(100).current,'E');
  assert.deepEqual(M.graphStep(0),M.graph.steps[0]);
  M.graph.steps.forEach((s,i)=>{
    assert.ok(M.graph.layers[s.layer].includes(s.current));
    if(s.edge)assert.ok(M.graph.edges[s.layer].some(e=>e.includes(s.edge[0])&&e.includes(s.edge[1])));
    if(i&&s.layer>M.graph.steps[i-1].layer)assert.equal(s.current,M.graph.steps[i-1].current);
  });
});
