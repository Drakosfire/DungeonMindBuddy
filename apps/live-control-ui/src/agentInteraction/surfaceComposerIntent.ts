/** Infer discussion versus a previewed surface edit; never authorizes mutation. */
export function classifySurfaceComposerIntent(message: string): "discuss" | "propose" {
  const normalized = message.trim()
    .replace(/^(?:please\s+)?(?:buddy[,!]?\s*)/i, "")
    .replace(/^for (?:this|the|our|my) [^,?.!]+,\s*/i, "");
  if (!normalized) return "discuss";
  const politePrefix = /^(?:(?:please|can you|could you|would you|can we|could we|i want you to|i'd like you to|i want to|i'd like to)\s+)+/i;
  const request = normalized.replace(politePrefix, "");
  const imageArtifact = /^(?:write|draft|prepare|make|create|generate|revise|rewrite|edit|turn)\s+(?:(?:this|that|it)\s+(?:as|into)\s+)?(?:(?:a|an|the|this|that)\s+)?(?:image(?:-generation)?\s+prompts?\b|prompts?\s+(?:for|to)\s+(?:(?:generate|generating|create|creating|make|making)\s+)?(?:(?:a|an|the|this|that)\s+)?(?:image|illustration|map)\b|(?:image|illustration|map)\b)/i;
  if (imageArtifact.test(request)) {
    // A destination must follow the requested artifact, or belong to a separate
    // positive mutation action. Context ("based on") and negation are not edits.
    const surfaceMutation = request.split(/[,;.!]|\b(?:and|then)\b/i).some(clause => {
      const action = clause.trim().replace(politePrefix, "");
      const artifact = imageArtifact.exec(action);
      if (artifact) {
        const destination = action.slice(artifact[0].length);
        return /^\s+(?:into|to|in|on)\s+(?:(?:this|the|our|my|selected|saved|current)\s+)*(?:plan|page|document|scene|card|beat)\b/i.test(destination)
          || /^\s+at\s+(?:(?:the|my|current|editor)\s+)+cursor\b/i.test(destination);
      }
      if (/^(?:replace|edit|revise|rewrite|update|change|remove|delete)\s+(?:(?:this|the|our|my|selected|saved|current)\s+)+(?:plan|page|document|scene|card|beat)\b/i.test(action)) return true;
      const mutation = /^(insert|add|append|put|place|remove|delete|replace|edit|revise|rewrite|update|change)\s+(.+)$/i.exec(action);
      if (!mutation) return false;
      // The changed object can be prose or a GM cue as well as an image.
      // Stop before contextual or negated wording so it cannot supply a target.
      const positiveObject = mutation[2].split(/\b(?:based on|using|without|instead of|rather than|do not|don't)\b/i)[0];
      return /\b(?:into|to|in|on)\s+(?:(?:this|the|our|my|selected|saved|current)\s+)*(?:plan|page|document|scene|card|beat)\b/i.test(positiveObject)
        || (/^(?:remove|delete)$/i.test(mutation[1]) && /\bfrom\s+(?:(?:this|the|our|my|selected|saved|current)\s+)*(?:plan|page|document|scene|card|beat)\b/i.test(positiveObject));
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
