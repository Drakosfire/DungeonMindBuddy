/** Infer discussion versus a previewed surface edit; never authorizes mutation. */
export function classifySurfaceComposerIntent(message: string): "discuss" | "propose" {
  const normalized = message.trim()
    .replace(/^(?:please\s+)?(?:buddy[,!]?\s*)/i, "")
    .replace(/^for (?:this|the|our|my) [^,?.!]+,\s*/i, "");
  if (!normalized) return "discuss";
  const request = normalized.replace(/^(?:(?:please|can you|could you|would you|can we|could we|i want you to|i'd like you to|i want to|i'd like to)\s+)+/i, "");
  const imageArtifact = /^(?:write|draft|prepare|make|create|generate|revise|rewrite|edit|turn)\s+(?:(?:this|that|it)\s+(?:as|into)\s+)?(?:(?:a|an|the|this|that)\s+)?(?:image(?:-generation)?\s+prompts?\b|prompts?\s+(?:for|to)\s+(?:(?:generate|generating|create|creating|make|making)\s+)?(?:(?:a|an|the|this|that)\s+)?(?:image|illustration|map)\b|(?:image|illustration|map)\b)/i.test(request);
  if (imageArtifact) {
    // Preparing an image artifact never edits a surface. An explicit surface
    // destination (including a second action) still uses the existing preview.
    const surfaceMutation = request.split(/[,;.!]|\b(?:and|then)\b/i).some(clause => {
      const action = clause.trim().replace(/^please\s+/i, "");
      if (!/^(?:write|draft|make|create|insert|add|append|put|place|replace|edit|revise|rewrite|update|change|remove|delete)\b/i.test(action)) return false;
      return /\b(?:into|to|in|on)\s+(?:(?:this|the|our|my|selected|saved|current)\s+)*(?:plan|page|document|scene|card|beat)\b/i.test(action)
        || /^(?:replace|edit|revise|rewrite|update|change|remove|delete)\s+(?:(?:this|the|our|my|selected|saved|current)\s+)+(?:plan|page|document|scene|card|beat)\b/i.test(action)
        || /^(?:remove|delete)\b.*\bfrom\s+(?:(?:this|the|our|my|selected|saved|current)\s+)*(?:plan|page|document|scene|card|beat)\b/i.test(action)
        || /\bat\s+(?:(?:the|my|current|editor)\s+)+cursor\b/i.test(action);
    });
    return surfaceMutation ? "propose" : "discuss";
  }
  const proposedEdit = "propose\\s+(?:to\\s+(?:append|edit|revise|rewrite|replace|update|add|remove|delete|change|insert|shorten|expand|move|reorder)|(?:appending|editing|revising|rewriting|replacing|updating|adding|removing|deleting|changing|inserting|shortening|expanding|moving|reordering))";
  const changeVerb = `(?:${proposedEdit}|append|edit|revise|rewrite|replace|update|add|remove|delete|change|insert|draft|write|shorten|expand|move|reorder|make)`;
  // Explicit change requests take precedence over interrogative phrasing (e.g. "Could you rewrite…?").
  if (new RegExp(`^(?:(?:please|can you|could you|would you|can we|could we|i want you to|i'd like you to|i want to|i'd like to)\\s+)?${changeVerb}\\b`, "i").test(normalized)) return "propose";
  if (new RegExp(`^(?:(?:can|could|would) you|(?:can|could) we|i want you to|i'd like you to|i want to|i'd like to)\\s+(?:please\\s+)?${changeVerb}\\b`, "i").test(normalized)) return "propose";
  if (/^(?:what|why|when|where|who|how|should|could|would|can we discuss|can we talk|is it possible to)\b/i.test(normalized)) return "discuss";
  return "discuss";
}
