"use server";

import { revalidatePath } from "next/cache";
import { supabase } from "@/lib/supabase";

export async function addRestaurant(formData: FormData) {
  const name = formData.get("name") as string;
  const menu = formData.get("menu") as string;
  const rating = Number(formData.get("rating"));
  const phone = (formData.get("phone") as string) || null;
  const address = (formData.get("address") as string) || null;
  const district = (formData.get("district") as string) || null;
  const neighborhood = (formData.get("neighborhood") as string) || null;
  const category = (formData.get("category") as string) || null;

  if (!name || !menu || !rating) return;

  const { error } = await supabase
    .from("restaurants")
    .insert({ name, menu, rating, phone, address, district, neighborhood, category });

  if (error) throw new Error(error.message);
  revalidatePath("/");
}

export async function updateRestaurant(id: string, formData: FormData) {
  const name = formData.get("name") as string;
  const menu = formData.get("menu") as string;
  const rating = Number(formData.get("rating"));
  const phone = (formData.get("phone") as string) || null;
  const address = (formData.get("address") as string) || null;
  const district = (formData.get("district") as string) || null;
  const neighborhood = (formData.get("neighborhood") as string) || null;
  const category = (formData.get("category") as string) || null;

  if (!name || !menu || !rating) return;

  const { error } = await supabase
    .from("restaurants")
    .update({ name, menu, rating, phone, address, district, neighborhood, category })
    .eq("id", id);

  if (error) throw new Error(error.message);
  revalidatePath("/");
}

export async function deleteRestaurant(id: string) {
  const { error } = await supabase
    .from("restaurants")
    .delete()
    .eq("id", id);

  if (error) throw new Error(error.message);
  revalidatePath("/");
}

type ImportRow = {
  name: string;
  menu: string;
  phone: string | null;
  address: string | null;
  district: string | null;
  neighborhood: string | null;
  rating: number;
  category: string | null;
};

export async function importRestaurants(restaurants: ImportRow[]) {
  const { error } = await supabase
    .from("restaurants")
    .insert(restaurants);

  if (error) throw new Error(error.message);
  revalidatePath("/");
}
