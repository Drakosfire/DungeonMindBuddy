export interface TextDiffLine { kind: "same" | "removed" | "added"; text: string }

/** Bounded line alignment; for very large edits preserve exact changed text without a quadratic allocation. */
export function workspaceTextDiff(saved: string, local: string): TextDiffLine[] {
  const a=saved.split("\n"), b=local.split("\n");
  let start=0, end=0;
  while(start<a.length && start<b.length && a[start]===b[start]) start++;
  while(end<a.length-start && end<b.length-start && a[a.length-1-end]===b[b.length-1-end]) end++;
  const left=a.slice(start,a.length-end), right=b.slice(start,b.length-end);
  const result:TextDiffLine[]=a.slice(0,start).map(text=>({kind:"same",text}));
  if((left.length+1)*(right.length+1)>200_000) {
    for(const text of left) result.push({kind:"removed",text});
    for(const text of right) result.push({kind:"added",text});
  } else {
    const width=right.length+1, scores=new Uint32Array((left.length+1)*width);
    for(let i=left.length-1;i>=0;i--) for(let j=right.length-1;j>=0;j--)
      scores[i*width+j]=left[i]===right[j]?scores[(i+1)*width+j+1]+1:Math.max(scores[(i+1)*width+j],scores[i*width+j+1]);
    let i=0,j=0;
    while(i<left.length || j<right.length) {
      if(i<left.length && j<right.length && left[i]===right[j]) result.push({kind:"same",text:left[i++]}),j++;
      else if(i<left.length && (j===right.length || scores[(i+1)*width+j]>=scores[i*width+j+1])) result.push({kind:"removed",text:left[i++]});
      else result.push({kind:"added",text:right[j++]});
    }
  }
  for(const text of a.slice(a.length-end)) result.push({kind:"same",text});
  return result;
}

export function diffWithContext(lines: TextDiffLine[]): (TextDiffLine | {kind:"omitted";text:string})[] {
  const output:(TextDiffLine | {kind:"omitted";text:string})[]=[];
  let omitted=0;
  for(let i=0;i<lines.length;i++) {
    const nearChange=lines.slice(Math.max(0,i-2),i+3).some(line=>line.kind!=="same");
    if(lines[i].kind==="same" && !nearChange) {omitted++;continue;}
    if(omitted) {output.push({kind:"omitted",text:`… ${omitted} unchanged line${omitted===1?"":"s"} …`});omitted=0;}
    output.push(lines[i]);
  }
  if(omitted) output.push({kind:"omitted",text:`… ${omitted} unchanged line${omitted===1?"":"s"} …`});
  return output;
}
