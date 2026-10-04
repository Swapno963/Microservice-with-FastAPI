import { useState } from "react";
import { useAuth } from "../auth";

const empty = { email: "", password: "", firstName: "", lastName: "" };

export default function AuthDialog() {
  const { authOpen, closeAuth, login, register, showNotice } = useAuth();
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const registerMode = mode === "register";

  if (!authOpen) return null;

  function update(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      if (registerMode) {
        await register({
          email: form.email,
          password: form.password,
          first_name: form.firstName,
          last_name: form.lastName,
        });
      } else {
        await login(form.email, form.password);
      }
      setForm(empty);
      setMode("signin");
      closeAuth();
      showNotice("You are signed in.");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="backdrop" onClick={closeAuth}>
      <div
        className="modal"
        role="dialog"
        aria-labelledby="auth-title"
        onClick={(event) => event.stopPropagation()}
      >
        <form onSubmit={onSubmit}>
          <button type="button" className="close" aria-label="Close" onClick={closeAuth}>
            ×
          </button>
          <h2 id="auth-title">{registerMode ? "Create an account" : "Sign in"}</h2>
          <label>
            Email
            <input
              name="email"
              type="email"
              autoComplete="email"
              required
              value={form.email}
              onChange={update}
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete={registerMode ? "new-password" : "current-password"}
              required
              minLength={registerMode ? 8 : undefined}
              value={form.password}
              onChange={update}
            />
          </label>
          {registerMode && (
            <>
              <p className="fine-print">
                At least 8 characters, with one uppercase letter, one lowercase letter, and one digit.
              </p>
              <label>
                First name
                <input name="firstName" autoComplete="given-name" required value={form.firstName} onChange={update} />
              </label>
              <label>
                Last name
                <input name="lastName" autoComplete="family-name" required value={form.lastName} onChange={update} />
              </label>
            </>
          )}
          {error && <p className="error">{error}</p>}
          <button className="button wide" type="submit" disabled={pending}>
            {registerMode ? "Create account" : "Sign in"}
          </button>
          <button
            className="link wide"
            type="button"
            onClick={() => {
              setMode(registerMode ? "signin" : "register");
              setError("");
            }}
          >
            {registerMode ? "I already have an account" : "Create an account"}
          </button>
        </form>
      </div>
    </div>
  );
}
