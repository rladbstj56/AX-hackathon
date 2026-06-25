"use client";

import { useState, useTransition, useMemo } from "react";
import { deleteRestaurant } from "@/app/actions";
import { Restaurant, CATEGORIES } from "@/types";
import EditModal from "@/components/EditModal";

function Stars({ rating }: { rating: number }) {
  return (
    <span className="text-lg tracking-wider">
      {[1, 2, 3, 4, 5].map((s) => (
        <span key={s} className={s <= rating ? "text-amber-400" : "text-gray-200"}>
          ★
        </span>
      ))}
    </span>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block px-2 py-0.5 bg-red-50 text-red-500 text-xs rounded-full font-medium">
      {children}
    </span>
  );
}

function RestaurantItem({ restaurant }: { restaurant: Restaurant }) {
  const [isPending, startTransition] = useTransition();
  const [editing, setEditing] = useState(false);

  return (
    <>
      {editing && (
        <EditModal restaurant={restaurant} onClose={() => setEditing(false)} />
      )}
      <li className="flex items-start justify-between bg-white rounded-2xl shadow-sm border border-gray-100 px-5 py-4 gap-3">
        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-bold text-gray-800">{restaurant.name}</p>
            {restaurant.category && <Badge>{restaurant.category}</Badge>}
          </div>
          <p className="text-sm text-gray-500">{restaurant.menu}</p>
          {(restaurant.district || restaurant.neighborhood) && (
            <p className="text-xs text-gray-400">
              📍 {[restaurant.district, restaurant.neighborhood].filter(Boolean).join(" ")}
            </p>
          )}
          {restaurant.address && (
            <p className="text-xs text-gray-400 truncate">{restaurant.address}</p>
          )}
          {restaurant.phone && (
            <p className="text-xs text-gray-400">📞 {restaurant.phone}</p>
          )}
          <Stars rating={restaurant.rating} />
        </div>
        <div className="flex flex-col gap-2 shrink-0 mt-0.5">
          <button
            onClick={() => setEditing(true)}
            className="text-gray-300 hover:text-blue-400 transition-colors text-sm leading-none"
            title="수정"
          >
            ✎
          </button>
          <button
            onClick={() => startTransition(() => deleteRestaurant(restaurant.id))}
            disabled={isPending}
            className="text-gray-300 hover:text-red-400 disabled:opacity-40 text-xl leading-none transition-colors"
            title="삭제"
          >
            ✕
          </button>
        </div>
      </li>
    </>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
        active
          ? "bg-red-500 text-white"
          : "bg-white text-gray-500 border border-gray-200 hover:border-red-300"
      }`}
    >
      {label}
    </button>
  );
}

export default function RestaurantList({ restaurants }: { restaurants: Restaurant[] }) {
  const [district, setDistrict] = useState<string>("전체");
  const [neighborhood, setNeighborhood] = useState<string>("전체");
  const [category, setCategory] = useState<string>("전체");

  const districts = useMemo(() => {
    const set = new Set(restaurants.map((r) => r.district).filter(Boolean) as string[]);
    return ["전체", ...Array.from(set).sort()];
  }, [restaurants]);

  const neighborhoods = useMemo(() => {
    const set = new Set(
      restaurants
        .filter((r) => district === "전체" || r.district === district)
        .map((r) => r.neighborhood)
        .filter(Boolean) as string[]
    );
    return ["전체", ...Array.from(set).sort()];
  }, [restaurants, district]);

  const filtered = useMemo(() => {
    return restaurants.filter((r) => {
      const matchDistrict = district === "전체" || r.district === district;
      const matchNeighborhood = neighborhood === "전체" || r.neighborhood === neighborhood;
      const matchCategory = category === "전체" || r.category === category;
      return matchDistrict && matchNeighborhood && matchCategory;
    });
  }, [restaurants, district, neighborhood, category]);

  if (restaurants.length === 0) {
    return (
      <p className="text-center text-gray-400 py-12 text-sm">
        등록된 맛집이 없습니다.
        <br />
        위에서 추가해보세요!
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {/* 지역 필터 */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">지역 (구)</p>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {districts.map((d) => (
            <FilterChip
              key={d}
              label={d}
              active={district === d}
              onClick={() => { setDistrict(d); setNeighborhood("전체"); }}
            />
          ))}
        </div>
      </div>

      {/* 동네 필터 */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">동네 (동)</p>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {neighborhoods.map((n) => (
            <FilterChip
              key={n}
              label={n}
              active={neighborhood === n}
              onClick={() => setNeighborhood(n)}
            />
          ))}
        </div>
      </div>

      {/* 카테고리 필터 */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">카테고리</p>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {["전체", ...CATEGORIES].map((c) => (
            <FilterChip
              key={c}
              label={c}
              active={category === c}
              onClick={() => setCategory(c)}
            />
          ))}
        </div>
      </div>

      {/* 결과 수 */}
      <p className="text-sm text-gray-400 px-1">
        {district !== "전체" || neighborhood !== "전체" || category !== "전체"
          ? `${filtered.length}개 검색됨 (전체 ${restaurants.length}개)`
          : `총 ${restaurants.length}개`}
      </p>

      {/* 목록 */}
      {filtered.length === 0 ? (
        <p className="text-center text-gray-400 py-8 text-sm">
          해당 조건의 맛집이 없습니다.
        </p>
      ) : (
        <ul className="space-y-3">
          {filtered.map((r) => (
            <RestaurantItem key={r.id} restaurant={r} />
          ))}
        </ul>
      )}
    </div>
  );
}
