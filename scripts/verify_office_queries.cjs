// Syntax acceptance with Microsoft's parser; this is not Excel runtime acceptance.
const fs=require('node:fs'),path=require('node:path');
const P=require(path.resolve(process.argv[2]));
(async()=>{
  const results=[];
  for(const name of ['FinancialEvidenceRows.pq','FinancialEvidenceFunding.pq','FinancialEvidenceWatchlist.pq']){
    const result=await P.TaskUtils.tryLexParse(P.DefaultSettings,fs.readFileSync(path.join(__dirname,'../docs/office',name),'utf8'));
    results.push({name,stage:result.stage,result:result.resultKind});
    if(result.resultKind!=='Ok')throw new Error('Power Query parse failed: '+name);
  }
  console.log(JSON.stringify({parser:'@microsoft/powerquery-parser@4.0.0',checks:results,scope:'syntax only; native Excel refresh pending'}));
})().catch(error=>{console.error(error.message);process.exitCode=1;});
