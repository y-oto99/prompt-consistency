/- Publication of a single document. Revisions are unbounded natural numbers. -/
namespace Approval

structure Draft where
  revision : Nat := 1
  reviewing : Option Nat := none
  approved : Option Nat := none
  active : Bool := false
  queued : Option Nat := none
  deriving DecidableEq

inductive State where
  | pending (d : Draft)
  | published (snapshot : Draft)
  deriving DecidableEq

def initial : Draft := {}

def versionsMatch (d : Draft) : Prop :=
  d.approved = some d.revision ∧ d.queued = some d.revision

def authorized (d : Draft) : Prop := versionsMatch d ∧ d.active = true

/-- The guard is tested at publication time. A publication freezes the record. -/
inductive Step (guard : Draft → Prop) : State → State → Prop where
  | edit (d) : Step guard (.pending d) (.pending { d with revision := d.revision + 1 })
  | request (d) : d.reviewing = none →
      Step guard (.pending d) (.pending { d with reviewing := some d.revision })
  | approve (d) (r) : d.reviewing = some r →
      Step guard (.pending d) (.pending { d with reviewing := none, approved := some r, active := true })
  | cancel (d) (r) : d.reviewing = some r →
      Step guard (.pending d) (.pending { d with reviewing := none })
  | revoke (d) : d.active = true →
      Step guard (.pending d) (.pending { d with active := false })
  | queue (d) : d.queued = none → d.active = true → d.approved = some d.revision →
      Step guard (.pending d) (.pending { d with queued := some d.revision })
  | clear (d) (r) : d.queued = some r → ¬ authorized d →
      Step guard (.pending d) (.pending { d with queued := none })
  | publish (d) : guard d → Step guard (.pending d) (.published d)

inductive Reachable (guard : Draft → Prop) : State → Prop where
  | start : Reachable guard (.pending initial)
  | next {s t} : Reachable guard s → Step guard s t → Reachable guard t

def Safe : State → Prop
  | .pending _ => True
  | .published d => authorized d

/-- Every finite history under the full guard preserves publication safety. -/
theorem guarded_safe {s} (h : Reachable authorized s) : Safe s := by
  induction h with
  | start => trivial
  | next _ step _ =>
    cases step <;> first | trivial | assumption

private def reviewing : Draft := { initial with reviewing := some 1 }
private def approved : Draft := { reviewing with reviewing := none, approved := some 1, active := true }
private def queued : Draft := { approved with queued := some 1 }
private def revoked : Draft := { queued with active := false }

private theorem can_queue (guard : Draft → Prop) : Reachable guard (.pending queued) := by
  exact .next (.next (.next .start (.request initial rfl)) (.approve reviewing 1 rfl))
    (.queue approved rfl rfl rfl)

/-- The strong guard still allows a real publication from the initial state. -/
theorem guarded_can_publish : ∃ d, Reachable authorized (.published d) :=
  ⟨queued, .next (can_queue authorized) (.publish queued ⟨⟨rfl, rfl⟩, rfl⟩)⟩

/-- Version equality alone lets a revoked approval reach publication. -/
theorem revision_only_counterexample :
    ∃ d, Reachable versionsMatch (.published d) ∧ ¬ Safe (.published d) := by
  refine ⟨revoked, .next (.next (can_queue versionsMatch) (.revoke queued rfl))
    (.publish revoked ⟨rfl, rfl⟩), ?_⟩
  intro h
  have impossible : false = true := h.2
  cases impossible

#print axioms guarded_safe
#print axioms guarded_can_publish
#print axioms revision_only_counterexample
end Approval
