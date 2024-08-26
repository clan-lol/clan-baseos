import { setActiveURI, setClanList } from "@/src/App";
import { registerClan } from "../settings";
import { useNavigate } from "@solidjs/router";

export const Welcome = () => {
  const navigate = useNavigate();
  return (
    <div class="hero min-h-[calc(100vh-10rem)]">
      <div class="hero-content mb-32 text-center">
        <div class="max-w-md">
          <h1 class="text-5xl font-bold">Welcome to Clan</h1>
          <p class="py-6">Own the services you use.</p>
          <div class="flex flex-col items-start gap-2">
            <button
              class="btn btn-primary w-full"
              onClick={() => navigate("/clan/create")}
            >
              Build your own
            </button>
            <button
              class="link w-full text-right text-primary"
              onClick={async () => {
                const uri = await registerClan();
                if (uri) {
                  setActiveURI(uri);
                  navigate("/machines");
                }
              }}
            >
              Or select folder
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
