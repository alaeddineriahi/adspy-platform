import { SignUp } from "@clerk/nextjs";
import { clerkTheme } from "../../theme";

export default function SignUpPage() {
  return <SignUp appearance={clerkTheme} />;
}
