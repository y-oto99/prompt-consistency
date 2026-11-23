/- A response is a list of classified passages; its text is not inspected by Lean.
   The current verification status belongs to the same member throughout. -/
namespace Disclosure

inductive Audience where
  | everyone
  | member
  deriving DecidableEq

structure Passage where
  audience : Audience
  text : String
  deriving DecidableEq

abbrev Answer := List Passage

/-- Current verification is consulted when sending, including a replay. -/
def permitted (verified : Bool) (p : Passage) : Prop :=
  p.audience = .everyone ∨ verified = true

def Safe (verified : Bool) (answer : Answer) : Prop :=
  ∀ p ∈ answer, permitted verified p

def publishable (verified : Bool) (answer : Answer) : Answer :=
  answer.filter (fun p => decide (p.audience = .everyone) || verified)

private def notice : Passage := ⟨.everyone, "手続きの案内です。"⟩
private def detail : Passage := ⟨.member, "会員限定の受付枠は午後です。"⟩
private def saved : Answer := [notice, detail]

/-- After verification expires, a verbatim replay of this saved answer violates
    the disclosure rule. The same answer was safe when it was prepared. -/
theorem replay_after_expiry :
    Safe true saved ∧ ¬ ∃ sent : Answer, sent = saved ∧ Safe false sent := by
  constructor
  · intro p _
    exact Or.inr rfl
  · rintro ⟨_, rfl, safe⟩
    have allowed := safe detail (by simp [saved])
    simp [permitted, detail] at allowed

/-- With an explicit replay exception, every passage actually sent is permitted,
    for any saved answer and any current verification status. -/
theorem filtered_replay_safe (verified : Bool) (answer : Answer) :
    Safe verified (publishable verified answer) := by
  intro p included
  have accepted := (List.mem_filter.mp included).2
  simpa [permitted] using accepted

/-- The policy preserves the full answer for a verified member and just
    the public passage for this example after verification expires. -/
theorem example_outputs :
    publishable true saved = saved ∧ publishable false saved = [notice] := by
  decide

#print axioms replay_after_expiry
#print axioms filtered_replay_safe
#print axioms example_outputs
end Disclosure
