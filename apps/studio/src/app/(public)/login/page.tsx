import { LocalSessionForm } from "../../../components/local-session-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const error = (await searchParams).auth_error;
  return (
    <main className="studio-state-wrap">
      <LocalSessionForm oidcError={typeof error === "string" ? error : null} />
    </main>
  );
}
