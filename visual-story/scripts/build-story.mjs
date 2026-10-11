import {readFile, writeFile, mkdir, cp} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
await mkdir(root+'dist/assets',{recursive:true});
let html=await readFile(root+'src/story.html','utf8');
for(const extension of ['js','css']){
 const content=await readFile(root+'src/story.'+extension);
 const hash=createHash('sha256').update(content).digest('hex').slice(0,12);
 const filename='story-'+hash+'.'+extension;
 const pattern=new RegExp('/assets/story-[A-Za-z0-9_-]+\\.'+extension,'g');
 if([...html.matchAll(pattern)].length!==1)throw new Error('Expected one story '+extension+' reference');
 await writeFile(root+'dist/assets/'+filename,content);
 html=html.replace(pattern,'/assets/'+filename);
}
await cp(root+'src/modulepreload-polyfill-B5Qt9EMX.js',root+'dist/assets/modulepreload-polyfill-B5Qt9EMX.js');
await cp(root+'../recovery/site-v10/story-data',root+'dist/story-data',{recursive:true});
await writeFile(root+'dist/story.html',html);
await writeFile(root+'dist/index.html',html);
console.log('Built standalone visual story. Original simulation core and preserved data unchanged.');
