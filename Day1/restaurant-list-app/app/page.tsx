import { supabase } from "@/lib/supabase";
import { Restaurant } from "@/types";
import RestaurantForm from "@/components/RestaurantForm";
import RestaurantList from "@/components/RestaurantList";
import ExcelImport from "@/components/ExcelImport";

async function getRestaurants(): Promise<Restaurant[]> {
  const { data, error } = await supabase
    .from("restaurants")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) return [];
  return data ?? [];
}

export default async function Home() {
  const restaurants = await getRestaurants();

  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold text-center text-red-500 mb-8">
        맛집 리스트
      </h1>

      <RestaurantForm />

      <div className="mt-4">
        <ExcelImport />
      </div>

      <div className="mt-8">
        <RestaurantList restaurants={restaurants} />
      </div>
    </main>
  );
}
