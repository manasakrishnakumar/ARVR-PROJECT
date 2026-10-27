import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="card">
      <h1>Page not found</h1>
      <p>That address does not exist in this app.</p>
      <Link className="btn primary" to="/">Back to the home page</Link>
    </section>
  );
}
