import { useNavigate } from "react-router-dom";
import AccountPanel from "../components/AccountPanel";
import { useAuth } from "../context/AuthContext";

export default function AccountPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  if (user) {
    return (
      <section className="card">
        <h1>Signed in as {user.username}</h1>
        <p>Your sessions and adaptive history are saved on this computer. Manage your data in Settings & privacy.</p>
        <div className="row">
          <button className="primary" onClick={() => nav("/dashboard")}>Go to dashboard</button>
          <button onClick={() => nav("/settings")}>Settings & privacy</button>
        </div>
      </section>
    );
  }
  return <AccountPanel onDone={() => nav("/dashboard")} />;
}
