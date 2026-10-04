import { useEffect, useState } from "react";
import { useAuth } from "../auth";

const emptyAddress = {
  line1: "",
  line2: "",
  city: "",
  state: "",
  postal_code: "",
  country: "",
  is_default: false,
};

export default function Account() {
  const { api, isSignedIn, openAuth, showNotice } = useAuth();
  const [profile, setProfile] = useState(null);
  const [profileError, setProfileError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [addressError, setAddressError] = useState("");
  const [address, setAddress] = useState(emptyAddress);

  async function load() {
    const me = await api("/api/v1/auth/users/me");
    setProfile(me);
  }

  useEffect(() => {
    if (!isSignedIn) return;
    load().catch((err) => setProfileError(err.message));
  }, [isSignedIn]);

  if (!isSignedIn) {
    return (
      <section>
        <div className="section-heading">
          <h1>Account</h1>
        </div>
        <p className="empty">
          Sign in to manage your profile.{" "}
          <button className="link" type="button" onClick={openAuth}>
            Sign in
          </button>
        </p>
      </section>
    );
  }

  async function saveProfile(event) {
    event.preventDefault();
    setProfileError("");
    try {
      const updated = await api("/api/v1/auth/users/me", {
        method: "PUT",
        body: {
          first_name: profile.first_name,
          last_name: profile.last_name,
          phone: profile.phone || null,
        },
      });
      setProfile(updated);
      showNotice("Profile saved.");
    } catch (err) {
      setProfileError(err.message);
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    setPasswordError("");
    const data = new FormData(event.target);
    try {
      await api("/api/v1/auth/users/me/password", {
        method: "PUT",
        body: {
          current_password: data.get("current_password"),
          new_password: data.get("new_password"),
        },
      });
      event.target.reset();
      showNotice("Password changed.");
    } catch (err) {
      setPasswordError(err.message);
    }
  }

  async function createAddress(event) {
    event.preventDefault();
    setAddressError("");
    try {
      await api("/api/v1/auth/users/me/addresses", {
        method: "POST",
        body: {
          ...address,
          line2: address.line2 || null,
        },
      });
      setAddress(emptyAddress);
      await load();
      showNotice("Address saved.");
    } catch (err) {
      setAddressError(err.message);
    }
  }

  if (!profile) return <p>{profileError || "Loading account…"}</p>;

  return (
    <section className="stack">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{profile.email}</p>
          <h1>Account</h1>
        </div>
      </div>

      <form className="panel stack" onSubmit={saveProfile}>
        <h2>Profile</h2>
        <label>
          First name
          <input
            value={profile.first_name}
            onChange={(event) => setProfile({ ...profile, first_name: event.target.value })}
            required
          />
        </label>
        <label>
          Last name
          <input
            value={profile.last_name}
            onChange={(event) => setProfile({ ...profile, last_name: event.target.value })}
            required
          />
        </label>
        <label>
          Phone
          <input
            value={profile.phone || ""}
            onChange={(event) => setProfile({ ...profile, phone: event.target.value })}
          />
        </label>
        {profileError && <p className="error">{profileError}</p>}
        <button className="button" type="submit">
          Save profile
        </button>
      </form>

      <form className="panel stack" onSubmit={changePassword}>
        <h2>Password</h2>
        <p className="muted">
          New passwords need 8 characters, one uppercase letter, one lowercase letter, and one digit.
        </p>
        <label>
          Current password
          <input name="current_password" type="password" autoComplete="current-password" required />
        </label>
        <label>
          New password
          <input name="new_password" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        {passwordError && <p className="error">{passwordError}</p>}
        <button className="button secondary" type="submit">
          Change password
        </button>
      </form>

      <section className="panel stack">
        <h2>Addresses</h2>
        {profile.addresses?.length ? (
          <ul className="stack">
            {profile.addresses.map((item) => (
              <li key={item.id}>
                {item.line1}
                {item.line2 ? `, ${item.line2}` : ""}, {item.city}, {item.state} {item.postal_code}, {item.country}
                {item.is_default ? " · Default" : ""}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No addresses yet. The first one becomes your default.</p>
        )}
        <form className="stack" onSubmit={createAddress}>
          <label>
            Address
            <input
              required
              value={address.line1}
              onChange={(event) => setAddress({ ...address, line1: event.target.value })}
            />
          </label>
          <label>
            Address line 2
            <input value={address.line2} onChange={(event) => setAddress({ ...address, line2: event.target.value })} />
          </label>
          <label>
            City
            <input required value={address.city} onChange={(event) => setAddress({ ...address, city: event.target.value })} />
          </label>
          <label>
            State or region
            <input required value={address.state} onChange={(event) => setAddress({ ...address, state: event.target.value })} />
          </label>
          <label>
            Postal code
            <input
              required
              value={address.postal_code}
              onChange={(event) => setAddress({ ...address, postal_code: event.target.value })}
            />
          </label>
          <label>
            Country
            <input
              required
              value={address.country}
              onChange={(event) => setAddress({ ...address, country: event.target.value })}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={address.is_default}
              onChange={(event) => setAddress({ ...address, is_default: event.target.checked })}
            />
            Default address
          </label>
          {addressError && <p className="error">{addressError}</p>}
          <button className="button" type="submit">
            Add address
          </button>
        </form>
      </section>
    </section>
  );
}
