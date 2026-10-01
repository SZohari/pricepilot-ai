// Web encodings only: preserve the original composition and generated PNGs.
const path=require('node:path');
const fs=require('node:fs/promises');
const sharp=require('sharp');
const root=path.resolve(__dirname,'..');
(async()=>{
  const output=path.join(root,'src/web/static/assets/images');
  await fs.mkdir(output,{recursive:true});
  for(const name of ['design-store','portrait-studio','cycle-workshop','watch-packing','watch-details','journey-stock','journey-compare','journey-review']){
    for(const width of [640,960,1536]){
      const destination=path.join(output,`${name}-${width}.webp`);
      const result=await sharp(path.join(root,'design/homepage',`${name}.png`))
        .resize({width,withoutEnlargement:true}).webp({quality:80,effort:6}).toFile(destination);
      console.log(path.basename(destination),result.size);
    }
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
