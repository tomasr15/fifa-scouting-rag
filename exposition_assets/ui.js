(function(){
  'use strict';
  const M=VectorLesson,$=id=>document.getElementById(id);
  const fmt=n=>n.toLocaleString('es-AR',{minimumFractionDigits:3,maximumFractionDigits:3});
  const line=(x1,y1,x2,y2,color='#cfd9e2',extra='')=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" ${extra}/>`;
  document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{
    document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    ['vectors','neighbors','hnsw'].forEach(id=>$(id).hidden=id!==button.dataset.tab);
  }));
  $('vectorPlot').innerHTML=`<defs><marker id="arrowBlue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#1e62be"/></marker><marker id="arrowOrange" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c44d12"/></marker></defs>
    ${line(50,235,570,235)}${line(310,35,310,405)}<circle cx="310" cy="235" r="155" fill="none" stroke="#dbe4ec" stroke-dasharray="4 5"/>
    <text x="575" y="258">X</text><text x="325" y="42">Y</text><text x="292" y="259">0</text>
    ${line(310,235,465,235,'#1e62be','stroke-width="5" marker-end="url(#arrowBlue)"')}<text x="460" y="270">a = (1, 0)</text>
    <g id="rotatingVector" class="moving" style="transform-origin:310px 235px">${line(310,235,465,235,'#c44d12','stroke-width="5" marker-end="url(#arrowOrange)"')}</g><circle cx="310" cy="235" r="5" fill="#132b41"/><text id="bLabel"></text><path id="angleArc" fill="none" stroke="#c44d12" stroke-width="2"/>`;
  function vectors(){
    const deg=+$('angle').value,v=M.atAngle(deg);$('angleValue').textContent=deg+'°';$('similarity').textContent=fmt(v.similarity);$('cosDistance').textContent=fmt(v.distance);
    $('rotatingVector').style.transform=`rotate(${-deg}deg)`;
    $('bLabel').setAttribute('x',310+165*v.x+18);$('bLabel').setAttribute('y',Math.max(72,235-165*v.y-8));$('bLabel').textContent='b';
    $('angleArc').setAttribute('d',deg?`M 365 235 A 55 55 0 0 0 ${310+55*v.x} ${235-55*v.y}`:'');
    $('angleMeaning').textContent=deg===0?'Misma dirección: máxima similitud.':deg===90?'Direcciones perpendiculares: similitud cero.':deg===180?'Direcciones opuestas: similitud −1.':deg<90?'Al aumentar el ángulo, disminuye la similitud.':'El coseno es negativo; la distancia supera 1.';
  }
  $('angle').addEventListener('input',vectors);document.querySelectorAll('[data-angle]').forEach(b=>b.addEventListener('click',()=>{$('angle').value=b.dataset.angle;vectors();}));$('resetVectors').onclick=()=>{$('angle').value=45;vectors();};vectors();

  const px=x=>310+x*45,py=y=>235-y*40;
  let grid='';for(let i=-5;i<=5;i++){grid+=line(px(i),py(-5),px(i),py(5),i===0?'#9bafc2':'#ecf0f5');grid+=line(px(-5),py(i),px(5),py(i),i===0?'#9bafc2':'#ecf0f5');if(i%2===0){grid+=`<text x="${px(i)-5}" y="${py(-5)+22}">${i}</text><text x="${px(-5)-26}" y="${py(i)+6}">${i}</text>`;}}
  $('neighborsPlot').innerHTML=grid+`<text x="547" y="457">X</text><text x="63" y="30">Y</text><g id="neighborRays"></g>`+M.profiles.map(p=>`<g id="profile-${p.id}"><circle cx="${px(p.x)}" cy="${py(p.y)}" r="10" stroke-width="3"/><text x="${px(p.x)+15}" y="${py(p.y)-10}">${p.id} · ${p.position}</text><text class="excluded" x="${px(p.x)-7}" y="${py(p.y)+7}" style="font-size:24px">×</text></g>`).join('')+`<g id="queryPoint" class="moving"><text x="-13" y="10" style="font-size:33px;fill:#c44d12">★</text><text x="18" y="26" style="font-weight:bold;fill:#c44d12">Q</text></g>`;
  function neighbors(){
    const q={x:+$('qx').value,y:+$('qy').value},k=+$('k').value,age=+$('age').value;
    ['qx','qy','k','age'].forEach(id=>$(id+'Value').textContent=$(id).value);
    const found=M.search(q,k,$('position').value,age),ids=new Set(found.results.map(p=>p.id)),eligible=new Set(found.eligible.map(p=>p.id));
    M.profiles.forEach(p=>{const g=$('profile-'+p.id),ok=eligible.has(p.id),selected=ids.has(p.id);g.querySelector('circle').setAttribute('fill',selected?'#1e62be':'white');g.querySelector('circle').setAttribute('stroke',ok?'#1e62be':'#9da9b4');g.querySelector('.excluded').style.display=ok?'none':'';g.style.opacity=ok?'1':'.45';});
    $('queryPoint').style.transform=`translate(${px(q.x)}px,${py(q.y)}px)`;
    $('neighborRays').innerHTML=found.results.map(p=>line(px(q.x),py(q.y),px(p.x),py(p.y),'#91b3de','stroke-dasharray="5 5"')).join('');
    $('resultCount').textContent=`${found.eligible.length} elegibles · ${found.results.length} de ${k} resultados`;
    $('rankingBody').innerHTML=found.results.map(p=>`<tr><td><b>${p.id}</b> · ${p.position}</td><td>${p.age}</td><td>${fmt(p.distance)}</td></tr>`).join('');
    $('emptyMessage').textContent=found.error||(found.eligible.length===0?'Ningún perfil cumple los filtros.':found.results.length<k?'Se muestran todos los elegibles; no se inventan candidatos.':'');
  }
  ['qx','qy','k','age'].forEach(id=>$(id).addEventListener('input',neighbors));$('position').onchange=neighbors;$('resetNeighbors').onclick=()=>{Object.entries({qx:4,qy:1,k:3,age:40,position:'Todas'}).forEach(([id,v])=>$(id).value=v);neighbors();};neighbors();

  let step=0;
  const nodes=Object.fromEntries(M.graph.nodes.map(n=>[n.id,n])), gy=l=>80+l*120;
  $('graphPlot').innerHTML=M.graph.layers.map((layer,l)=>`<text x="15" y="${gy(l)-38}" style="font-size:15px">${['Capa superior','Capa intermedia','Capa base'][l]}</text>`+M.graph.edges[l].map(([a,b])=>line(nodes[a].x,gy(l),nodes[b].x,gy(l),'#cfd9e2',`id="edge-${l}-${a}-${b}" class="graph-edge" stroke-width="3"`)).join('')+layer.map(id=>`<g><circle id="node-${l}-${id}" class="graph-node" cx="${nodes[id].x}" cy="${gy(l)}" r="19" fill="white" stroke="#8ca3b7" stroke-width="2"/><text x="${nodes[id].x}" y="${gy(l)+6}" text-anchor="middle" id="label-${l}-${id}">${id}</text></g>`).join('')).join('')+line(M.graph.query,35,M.graph.query,355,'#c44d12','stroke-dasharray="5 6"')+`<text x="${M.graph.query+12}" y="33" style="fill:#c44d12">Q</text><path id="layerMarker" fill="#c44d12"/><text id="candidateDistance" x="930" y="385" text-anchor="end" style="font-size:15px"></text>`;
  function graph(){
    const s=M.graphStep(step);$('stepCount').textContent=`Paso ${step+1} de ${M.graph.steps.length}`;$('stepDetail').textContent=s.text;$('prevStep').disabled=step===0;$('nextStep').disabled=step===M.graph.steps.length-1;
    M.graph.layers.forEach((layer,l)=>{layer.forEach(id=>{const active=l===s.layer&&id===s.current,seen=l===s.layer&&s.seen.includes(id),circle=$(`node-${l}-${id}`);circle.setAttribute('fill',active?'#1e62be':seen?'#d7e6f8':'white');circle.setAttribute('stroke',active?'#1e62be':seen?'#1e62be':'#8ca3b7');circle.setAttribute('stroke-width',seen?'4':'2');$(`label-${l}-${id}`).style.fill=active?'white':'#132b41';});M.graph.edges[l].forEach(([a,b])=>{const active=l===s.layer&&s.edge&&s.edge.includes(a)&&s.edge.includes(b);$(`edge-${l}-${a}-${b}`).setAttribute('stroke',active?'#c44d12':'#cfd9e2');});});
    $('layerMarker').setAttribute('d',`M 43 ${gy(s.layer)-10} L 58 ${gy(s.layer)} L 43 ${gy(s.layer)+10} Z`);
    $('candidateDistance').textContent=`Candidato ${s.current} · distancia a Q: ${Math.abs(M.graph.query-nodes[s.current].x)} unidades`;
  }
  $('prevStep').onclick=()=>{step=Math.max(0,step-1);graph();};$('nextStep').onclick=()=>{step=Math.min(M.graph.steps.length-1,step+1);graph();};$('resetGraph').onclick=()=>{step=0;graph();};graph();
})();
