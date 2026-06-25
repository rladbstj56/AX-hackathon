export interface Restaurant {
  id: string;
  name: string;
  menu: string;
  rating: number;
  phone: string | null;
  address: string | null;
  district: string | null;
  neighborhood: string | null;
  category: string | null;
  created_at: string;
}

export const CATEGORIES = ["한식", "일식", "중식", "양식", "카페/디저트", "기타"] as const;
export type Category = (typeof CATEGORIES)[number];
