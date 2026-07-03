import { SignIn } from "@clerk/nextjs";
import { clerkTheme } from "../../theme";

export default function SignInPage() {
  return <SignIn appearance={clerkTheme} />;
}
