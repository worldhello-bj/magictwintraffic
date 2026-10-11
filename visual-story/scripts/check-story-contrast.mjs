// WCAG relative-luminance contrast for the revised text palette and its surfaces.
import assert from 'node:assert/strict';
function luminance(hex) {
  const linear = [1,3,5].map(i => parseInt(hex.slice(i,i+2),16)/255).map(x => x <= .04045 ? x/12.92 : ((x+.055)/1.055)**2.4);
  return linear.reduce((total,x,i) => total+x*[.2126,.7152,.0722][i],0);
}
const backgrounds=['#f5f3ed','#f9f9f1','#fcfcf6','#f9faf1','#e9eedf','#e9ecdf','#eceee3','#fbfcf4'];
for (const foreground of ['#475c50','#52665a','#854c35','#3c6548']) {
  const ratios=backgrounds.map(background => (luminance(background)+.05)/(luminance(foreground)+.05));
  assert.ok(Math.min(...ratios)>=4.5);
  console.log(`${foreground}: minimum ${Math.min(...ratios).toFixed(2)}:1 across ${backgrounds.length} surfaces`);
}
