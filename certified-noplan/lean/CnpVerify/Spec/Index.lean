/-
CnpVerify.Spec.Index — the flat layout of a coefficient tensor (L2: proofs).

A tensor of `n` variables and degree `≤ d` per variable is an array of `(d+1)^n` rationals; the
exponent vector `e` sits at `flatIndex (d+1) e = Σᵢ eᵢ (d+1)^(n-1-i)`. This file proves what the
tensor lemmas need from that layout: the sum formula, the bijection between exponent vectors in the
box and flat indices (`boxEquiv`), and that the executable `encode` / `decode` compute it.

It also turns the `for` loops of the executable definitions into folds (`forIn_list_id`,
`forIn_array_id`) so that they can be reasoned about by invariant.
-/
import Mathlib
import CnpVerify.Tensor

namespace CnpVerify

/-! ### `for` loops in `Id` are folds -/

/-- A `for` loop over a list in `Id` whose body always continues is a `foldl`. -/
theorem forIn_list_id {α β : Type} (l : List α) (init : β) (f : α → β → Id (ForInStep β))
    (g : β → α → β) (h : ∀ a b, f a b = pure (ForInStep.yield (g b a))) :
    (forIn l init f : Id β) = pure (l.foldl g init) := by
  have hf : f = fun a b => pure (ForInStep.yield (g b a)) := by
    funext a b
    exact h a b
  subst hf
  exact List.forIn_pure_yield_eq_foldl _ _

/-- A `for` loop over an array in `Id` whose body always continues is a `foldl`. -/
theorem forIn_array_id {α β : Type} (xs : Array α) (init : β) (f : α → β → Id (ForInStep β))
    (g : β → α → β) (h : ∀ a b, f a b = pure (ForInStep.yield (g b a))) :
    (forIn xs init f : Id β) = pure (xs.foldl g init) := by
  have hf : f = fun a b => pure (ForInStep.yield (g b a)) := by
    funext a b
    exact h a b
  subst hf
  exact Array.forIn_pure_yield_eq_foldl _ _

/-- Invariant rule for a fold over `0, 1, …, N-1`. -/
theorem foldl_range_induction {β : Type} (N : ℕ) (f : β → ℕ → β) (init : β) (P : ℕ → β → Prop)
    (h0 : P 0 init) (hstep : ∀ k, k < N → ∀ b, P k b → P (k + 1) (f b k)) :
    P N ((List.range N).foldl f init) := by
  induction N with
  | zero => simpa using h0
  | succ N ih =>
    rw [List.range_succ, List.foldl_append]
    simp only [List.foldl_cons, List.foldl_nil]
    exact hstep N (Nat.lt_succ_self N) _ (ih (fun k hk => hstep k (Nat.lt_succ_of_lt hk)))

/-- Invariant rule for a fold over a list: the invariant may use membership. -/
theorem foldl_list_induction {α β : Type} (l : List α) (f : β → α → β) (init : β) (P : β → Prop)
    (h0 : P init) (hstep : ∀ a ∈ l, ∀ b, P b → P (f b a)) : P (l.foldl f init) := by
  induction l generalizing init with
  | nil => simpa using h0
  | cons a l ih =>
    simp only [List.foldl_cons]
    exact ih _ (hstep a (by simp) _ h0) (fun a' ha' => hstep a' (by simp [ha']))

namespace Tensor

variable {n : ℕ}

/-! ### `flatIndex` -/

theorem flatIndex_succ_last (base : ℕ) (e : Fin (n + 1) → ℕ) :
    flatIndex base e = flatIndex base (fun i : Fin n => e i.castSucc) * base + e (Fin.last n) := by
  simp [flatIndex, Fin.foldl_succ_last]

/-- The flat index is the base-`base` number whose digits are the exponents, first variable
most significant. -/
theorem flatIndex_eq_sum (base : ℕ) (e : Fin n → ℕ) :
    flatIndex base e = ∑ i : Fin n, e i * base ^ (n - 1 - i.val) := by
  induction n with
  | zero => simp [flatIndex]
  | succ n ih =>
    rw [flatIndex_succ_last, ih, Fin.sum_univ_castSucc, Finset.sum_mul]
    congr 1
    · apply Finset.sum_congr rfl
      intro i _
      have hi : n + 1 - 1 - (i.castSucc : ℕ) = (n - 1 - i.val) + 1 := by
        have := i.isLt
        simp only [Fin.val_castSucc]
        omega
      rw [hi, pow_succ, mul_assoc]
    · simp

/-- The flat index is additive in the exponent vector. -/
theorem flatIndex_add (base : ℕ) (e e' : Fin n → ℕ) :
    flatIndex base (fun i => e i + e' i) = flatIndex base e + flatIndex base e' := by
  simp only [flatIndex_eq_sum, add_mul, Finset.sum_add_distrib]

/-- Exponent vectors of the box `{0..base-1}ⁿ` ≃ flat indices `< base^n` (first variable most
significant: Mathlib's `finFunctionFinEquiv` read from the last variable). -/
def boxEquiv (base n : ℕ) : (Fin n → Fin base) ≃ Fin (base ^ n) :=
  (Equiv.arrowCongr Fin.revPerm (Equiv.refl _)).trans finFunctionFinEquiv

theorem boxEquiv_val (base : ℕ) (e : Fin n → Fin base) :
    ((boxEquiv base n e : Fin (base ^ n)) : ℕ) = flatIndex base (fun i => (e i : ℕ)) := by
  rw [flatIndex_eq_sum]
  simp only [boxEquiv, Equiv.trans_apply, finFunctionFinEquiv_apply]
  rw [← Equiv.sum_comp Fin.revPerm (fun i : Fin n => (e i : ℕ) * base ^ (n - 1 - i.val))]
  apply Finset.sum_congr rfl
  intro i _
  have hi : n - 1 - (n - (i.val + 1)) = i.val := by
    have := i.isLt
    omega
  simp [Equiv.arrowCongr, hi]

theorem boxEquiv_symm_val (base : ℕ) (j : Fin (base ^ n)) (i : Fin n) :
    (((boxEquiv base n).symm j i : Fin base) : ℕ) = j.val / base ^ (n - 1 - i.val) % base := by
  have hi : n - (i.val + 1) = n - 1 - i.val := by omega
  simp [boxEquiv, Equiv.arrowCongr, finFunctionFinEquiv_symm_apply_val, hi]

/-- Exponent vectors in the box have a flat index inside the layout. -/
theorem flatIndex_lt (base : ℕ) (e : Fin n → Fin base) :
    flatIndex base (fun i => (e i : ℕ)) < base ^ n := by
  rw [← boxEquiv_val]
  exact (boxEquiv base n e).isLt

/-- The flat index is injective on the box. -/
theorem flatIndex_injective (base : ℕ) (e e' : Fin n → Fin base)
    (h : flatIndex base (fun i => (e i : ℕ)) = flatIndex base (fun i => (e' i : ℕ))) : e = e' := by
  rw [← boxEquiv_val, ← boxEquiv_val] at h
  exact (boxEquiv base n).injective (Fin.ext h)

/-- The digit of `flatIndex e` along `i` is `e i`. -/
theorem flatIndex_digit (base : ℕ) (e : Fin n → Fin base) (i : Fin n) :
    flatIndex base (fun i => (e i : ℕ)) / base ^ (n - 1 - i.val) % base = e i := by
  have h := boxEquiv_symm_val base (boxEquiv base n e) i
  rw [Equiv.symm_apply_apply, boxEquiv_val] at h
  exact h.symm

/-- A sum over the flat indices of the layout is a sum over the exponent vectors of the box. -/
theorem sum_range_eq_sum_box {M : Type*} [AddCommMonoid M] (base : ℕ) (F : ℕ → M) :
    ∑ idx ∈ Finset.range (base ^ n), F idx
      = ∑ e : Fin n → Fin base, F (flatIndex base (fun i => (e i : ℕ))) := by
  rw [← Fin.sum_univ_eq_sum_range, ← Equiv.sum_comp (boxEquiv base n)]
  apply Finset.sum_congr rfl
  intro e _
  rw [boxEquiv_val]

/-! ### `encode` and `decode` -/

/-- `encode` is `flatIndex` on the exponent array. -/
theorem encode_eq_flatIndex (n base : ℕ) (e : Array ℕ) :
    encode n base e = flatIndex base (fun i : Fin n => e.getD i.val 0) := by
  induction n with
  | zero => simp [encode, flatIndex]
  | succ n ih =>
    rw [flatIndex_succ_last]
    simp only [Fin.val_castSucc, Fin.val_last]
    rw [← ih]
    simp [encode, Nat.fold_succ]

theorem decode_eq_foldl (n base idx : ℕ) :
    decode n base idx
      = ((List.range n).foldl
          (fun (s : Array ℕ × ℕ) k => (s.1.set! (n - 1 - k) (s.2 % base), s.2 / base))
          (Array.replicate n 0, idx)).1 := by
  unfold decode
  simp only [Std.Legacy.Range.forIn_eq_forIn_range', Std.Legacy.Range.size]
  rw [forIn_list_id _ _ _
    (fun (s : Array ℕ × ℕ) k => (s.1.set! (n - 1 - k) (s.2 % base), s.2 / base))
    (fun _ _ => rfl)]
  simp [List.range_eq_range']

/-- `decode` writes the `n` digits of `idx`, first variable most significant. -/
theorem decode_spec (n base idx : ℕ) :
    (decode n base idx).size = n ∧
      ∀ i, i < n → (decode n base idx).getD i 0 = idx / base ^ (n - 1 - i) % base := by
  rw [decode_eq_foldl]
  have key := foldl_range_induction n
    (fun (s : Array ℕ × ℕ) k => (s.1.set! (n - 1 - k) (s.2 % base), s.2 / base))
    (Array.replicate n 0, idx)
    (fun k s => s.1.size = n ∧ s.2 = idx / base ^ k ∧
      ∀ i, i < n → n - k ≤ i → s.1.getD i 0 = idx / base ^ (n - 1 - i) % base)
    ⟨by simp, by simp, fun i hi hk => by omega⟩
    (by
      rintro k hk ⟨out, r⟩ ⟨hsz, hr, hd⟩
      simp only at hsz hr hd ⊢
      refine ⟨by simp [hsz], ?_, ?_⟩
      · rw [hr, Nat.div_div_eq_div_mul, pow_succ]
      · intro i hi hki
        by_cases hik : n - 1 - k = i
        · subst hik
          have hlt : n - 1 - k < out.size := by omega
          have hexp : n - 1 - (n - 1 - k) = k := by omega
          simp [hlt, hr, hexp]
        · have := hd i hi (by omega)
          simpa [Array.getElem?_setIfInBounds, hik] using this)
  exact ⟨key.1, fun i hi => key.2.2 i hi (by omega)⟩

end Tensor

end CnpVerify
