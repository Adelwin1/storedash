"use client";

import {
  useEffect,
  useState,
} from "react";

import { api } from "@/lib/api";


type Category = {
  id: number;
  code: string;
  name: string;

  fallback_small_units: number;
  fallback_medium_units: number;
  fallback_large_units: number;
};


type LogisticsType = {
  id: number;
  category_id: number;

  name: string;
  package_type: string;

  load_units: number;
};


type Variant = {
  key: string;
  label: string;

  physical_size_text: string;
  size_class: string;
};


type CargoEstimate = {
  profile_version: string;

  category_code: string;
  material_class: string;

  package_type: string;
  size_class: string;

  weight_kg_each: number;
  volume_l_each: number;

  handling_score_each: number;
  fragility_score_each: number;

  load_units_each: number;

  confidence: number;

  estimation_source: string;

  explicit_mass_found: boolean;
  explicit_volume_found: boolean;
  multipack_found: boolean;
};


type UpdatedOrder = {
  items: Array<{
    id: number;

    logistics_variant_key?:
      string | null;

    logistics_size_detail?:
      string | null;

    physical_material_class?:
      string | null;

    physical_estimation_source?:
      string | null;

    physical_confidence?:
      number | null;

    weight_kg_each?:
      number | null;

    volume_l_each?:
      number | null;

    handling_score_each?:
      number | null;

    fragility_score_each?:
      number | null;

    load_units_each?:
      number | null;

    total_load_units?:
      number | null;

    total_weight_kg?:
      number | null;

    total_volume_l?:
      number | null;
  }>;
};


export default function OrderItemLogistics({
  orderId,
  itemId,

  productName,
  productSize,

  editable,

  savedCategoryId,
  savedTypeId,
  savedSizeClass,

  savedVariantKey,
  savedSizeDetail,

  savedMaterialClass,
  savedPhysicalConfidence,
  savedEstimationSource,

  savedWeightEach,
  savedVolumeEach,

  savedHandlingEach,
  savedFragilityEach,

  savedLoadUnitsEach,
  savedTotalLoadUnits,
}: {
  orderId: number;

  itemId: number;

  productName: string;

  productSize?:
    string | null;

  editable: boolean;

  savedCategoryId?:
    number | null;

  savedTypeId?:
    number | null;

  savedSizeClass?:
    string | null;

  savedVariantKey?:
    string | null;

  savedSizeDetail?:
    string | null;

  savedMaterialClass?:
    string | null;

  savedPhysicalConfidence?:
    number | null;

  savedEstimationSource?:
    string | null;

  savedWeightEach?:
    number | null;

  savedVolumeEach?:
    number | null;

  savedHandlingEach?:
    number | null;

  savedFragilityEach?:
    number | null;

  savedLoadUnitsEach?:
    number | null;

  savedTotalLoadUnits?:
    number | null;
}) {

  const [
    categories,
    setCategories,
  ] = useState<Category[]>([]);


  const [
    types,
    setTypes,
  ] = useState<
    LogisticsType[]
  >([]);


  const [
    variants,
    setVariants,
  ] = useState<
    Variant[]
  >([]);


  const [
    categoryId,
    setCategoryId,
  ] = useState(
    savedCategoryId
      ? String(savedCategoryId)
      : ""
  );


  const [
    typeId,
    setTypeId,
  ] = useState(
    savedTypeId
      ? String(savedTypeId)
      : ""
  );


  const [
    variantKey,
    setVariantKey,
  ] = useState(
    savedVariantKey || ""
  );


  const [
    sizeClass,
    setSizeClass,
  ] = useState(
    savedSizeClass || "medium"
  );


  const [
    physicalSizeText,
    setPhysicalSizeText,
  ] = useState(
    savedSizeDetail
    || productSize
    || ""
  );


  const [
    estimate,
    setEstimate,
  ] = useState<
    CargoEstimate | null
  >(null);


  const [
    totalLoadUnits,
    setTotalLoadUnits,
  ] = useState<
    number | null
  >(
    savedTotalLoadUnits
    ?? null
  );


  const [
    loading,
    setLoading,
  ] = useState(true);


  const [
    previewing,
    setPreviewing,
  ] = useState(false);


  const [
    saving,
    setSaving,
  ] = useState(false);


  const [
    message,
    setMessage,
  ] = useState("");


  const [
    error,
    setError,
  ] = useState("");


  async function loadTypes(
    selectedCategoryId: number
  ) {

    const data =
      await api<
        LogisticsType[]
      >(
        `/logistics/types?category_id=${selectedCategoryId}`
      );


    setTypes(data);

    return data;
  }


  async function loadVariants(
    selectedCategoryId: number,
    selectedTypeId: number,
  ) {

    const data =
      await api<
        Variant[]
      >(
        `/logistics/variants?category_id=${selectedCategoryId}&logistics_type_id=${selectedTypeId}`
      );


    setVariants(data);

    return data;
  }


  async function previewCargo(
    nextCategoryId:
      string,

    nextTypeId:
      string,

    nextSizeClass:
      string,

    nextSizeText:
      string,
  ) {

    if (
      !nextCategoryId
      || !nextTypeId
    ) {
      setEstimate(null);
      return;
    }


    try {

      setPreviewing(true);
      setError("");


      const result =
        await api<
          CargoEstimate
        >(
          "/logistics/estimate",
          {
            method:
              "POST",

            body:
              JSON.stringify({
                product_name:
                  productName,

                category_id:
                  Number(
                    nextCategoryId
                  ),

                logistics_type_id:
                  Number(
                    nextTypeId
                  ),

                size_class:
                  nextSizeClass,

                physical_size_text:
                  nextSizeText
                  || null,
              }),
          }
        );


      setEstimate(result);


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not estimate cargo."
      );


    } finally {

      setPreviewing(false);
    }
  }


  useEffect(() => {

    async function initialize() {

      try {

        const categoryData =
          await api<
            Category[]
          >(
            "/logistics/categories"
          );


        setCategories(
          categoryData
        );


        if (
          savedCategoryId
        ) {

          await loadTypes(
            savedCategoryId
          );


          if (
            savedTypeId
          ) {

            await loadVariants(
              savedCategoryId,
              savedTypeId,
            );


            await previewCargo(
              String(
                savedCategoryId
              ),

              String(
                savedTypeId
              ),

              savedSizeClass
              || "medium",

              savedSizeDetail
              || productSize
              || "",
            );
          }


          return;
        }


        const resolved =
          await api<{
            category_id:
              number;

            logistics_type_id:
              number | null;

            size_class:
              string;
          }>(
            `/logistics/resolve?product_name=${encodeURIComponent(
              productName
            )}`
          );


        const resolvedCategory =
          String(
            resolved.category_id
          );


        setCategoryId(
          resolvedCategory
        );


        setSizeClass(
          resolved.size_class
          || "medium"
        );


        await loadTypes(
          resolved.category_id
        );


        if (
          resolved.logistics_type_id
        ) {

          const resolvedType =
            String(
              resolved.logistics_type_id
            );


          setTypeId(
            resolvedType
          );


          await loadVariants(
            resolved.category_id,
            resolved.logistics_type_id,
          );


          await previewCargo(
            resolvedCategory,
            resolvedType,

            resolved.size_class
            || "medium",

            productSize
            || "",
          );
        }


      } catch (error) {

        setError(
          error instanceof Error
            ? error.message
            : "Could not load logistics."
        );


      } finally {

        setLoading(false);
      }
    }


    initialize();

  }, [
    productName,
    savedCategoryId,
    savedTypeId,
  ]);


  async function categoryChanged(
    value: string
  ) {

    setCategoryId(value);

    setTypeId("");
    setVariantKey("");

    setTypes([]);
    setVariants([]);

    setEstimate(null);

    setPhysicalSizeText(
      productSize
      || ""
    );


    if (!value) {
      return;
    }


    try {

      await loadTypes(
        Number(value)
      );


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not load package types."
      );
    }
  }


  async function typeChanged(
    value: string
  ) {

    setTypeId(value);

    setVariantKey("");

    setVariants([]);

    setEstimate(null);


    if (
      !value
      || !categoryId
    ) {
      return;
    }


    try {

      await loadVariants(
        Number(categoryId),
        Number(value),
      );


      if (
        physicalSizeText
      ) {

        await previewCargo(
          categoryId,
          value,
          sizeClass,
          physicalSizeText,
        );
      }


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not load variants."
      );
    }
  }


  async function variantChanged(
    value: string
  ) {

    setVariantKey(value);


    const selected =
      variants.find(
        (variant) =>
          variant.key
          === value
      );


    if (!selected) {
      return;
    }


    if (
      selected.key
      === "custom"
    ) {

      setPhysicalSizeText("");

      setEstimate(null);

      return;
    }


    setSizeClass(
      selected.size_class
    );


    setPhysicalSizeText(
      selected.physical_size_text
    );


    await previewCargo(
      categoryId,
      typeId,

      selected.size_class,
      selected.physical_size_text,
    );
  }


  async function customSizeChanged(
    value: string
  ) {

    setPhysicalSizeText(
      value
    );
  }


  async function saveClassification() {

    if (!categoryId) {

      setError(
        "Select a product category."
      );

      return;
    }


    if (!typeId) {

      setError(
        "Select a package or product form."
      );

      return;
    }


    try {

      setSaving(true);

      setError("");
      setMessage("");


      const updated =
        await api<
          UpdatedOrder
        >(
          `/orders/${orderId}/items/${itemId}/logistics`,
          {
            method:
              "PUT",

            body:
              JSON.stringify({
                category_id:
                  Number(
                    categoryId
                  ),

                logistics_type_id:
                  Number(
                    typeId
                  ),

                size_class:
                  sizeClass,

                variant_key:
                  variantKey
                  || null,

                physical_size_text:
                  physicalSizeText
                  || null,
              }),
          }
        );


      await api(
        "/logistics/learn-product",
        {
          method:
            "POST",

          body:
            JSON.stringify({
              product_name:
                productName,

              category_id:
                Number(
                  categoryId
                ),

              logistics_type_id:
                Number(
                  typeId
                ),

              size_class:
                sizeClass,
            }),
        }
      );


      const updatedItem =
        updated.items.find(
          (item) =>
            item.id
            === itemId
        );


      if (
        updatedItem
      ) {

        setTotalLoadUnits(
          updatedItem
            .total_load_units
          ?? null
        );


        if (
          updatedItem.weight_kg_each
          != null
          &&
          updatedItem.volume_l_each
          != null
        ) {

          setEstimate({
            profile_version:
              "",

            category_code:
              "",

            material_class:
              updatedItem
                .physical_material_class
              || "",

            package_type:
              "",

            size_class:
              sizeClass,

            weight_kg_each:
              updatedItem
                .weight_kg_each,

            volume_l_each:
              updatedItem
                .volume_l_each,

            handling_score_each:
              updatedItem
                .handling_score_each
              ?? 0,

            fragility_score_each:
              updatedItem
                .fragility_score_each
              ?? 0,

            load_units_each:
              updatedItem
                .load_units_each
              ?? 0,

            confidence:
              updatedItem
                .physical_confidence
              ?? 0,

            estimation_source:
              updatedItem
                .physical_estimation_source
              || "",

            explicit_mass_found:
              false,

            explicit_volume_found:
              false,

            multipack_found:
              false,
          });
        }
      }


      setMessage(
        "Physical logistics profile saved."
      );


    } catch (error) {

      setError(
        error instanceof Error
          ? error.message
          : "Could not save logistics."
      );


    } finally {

      setSaving(false);
    }
  }


  const selectedType =
    types.find(
      (type) =>
        type.id
        === Number(typeId)
    );


  if (loading) {

    return (
      <div className="label">
        Loading logistics...
      </div>
    );
  }


  return (
    <div
      style={{
        display: "grid",
        gap: 14,
      }}
    >

      <div className="form-grid">

        <label>
          Product Category

          <select
            className="input"

            value={
              categoryId
            }

            disabled={
              !editable
            }

            onChange={(
              event
            ) =>
              categoryChanged(
                event.target.value
              )
            }
          >
            <option value="">
              Select category
            </option>

            {
              categories.map(
                (
                  category
                ) => (
                  <option
                    key={
                      category.id
                    }

                    value={
                      category.id
                    }
                  >
                    {
                      category.name
                    }
                  </option>
                )
              )
            }
          </select>
        </label>


        <label>
          Package / Product Form

          <select
            className="input"

            value={
              typeId
            }

            disabled={
              !editable
              || !categoryId
            }

            onChange={(
              event
            ) =>
              typeChanged(
                event.target.value
              )
            }
          >
            <option value="">
              Select package
            </option>

            {
              types.map(
                (
                  type
                ) => (
                  <option
                    key={
                      type.id
                    }

                    value={
                      type.id
                    }
                  >
                    {
                      type.name
                    }
                  </option>
                )
              )
            }
          </select>
        </label>


        <label>
          Exact Logistics Variant

          <select
            className="input"

            value={
              variantKey
            }

            disabled={
              !editable
              || !typeId
            }

            onChange={(
              event
            ) =>
              variantChanged(
                event.target.value
              )
            }
          >
            <option value="">
              Select exact size
            </option>

            {
              variants.map(
                (
                  variant
                ) => (
                  <option
                    key={
                      variant.key
                    }

                    value={
                      variant.key
                    }
                  >
                    {
                      variant.label
                    }
                  </option>
                )
              )
            }
          </select>
        </label>


        {
          variantKey
          === "custom"
          && (
            <label>
              Physical Size

              <input
                className="input"

                placeholder={
                  "e.g. 25kg, 5L, 24 x 500ml"
                }

                value={
                  physicalSizeText
                }

                disabled={
                  !editable
                }

                onChange={(
                  event
                ) =>
                  customSizeChanged(
                    event.target.value
                  )
                }

                onBlur={() =>
                  previewCargo(
                    categoryId,
                    typeId,
                    sizeClass,
                    physicalSizeText,
                  )
                }
              />
            </label>
          )
        }


        <label>
          Size Class

          <select
            className="input"

            value={
              sizeClass
            }

            disabled={
              !editable
            }

            onChange={(
              event
            ) => {

              const next =
                event.target.value;


              setSizeClass(next);


              previewCargo(
                categoryId,
                typeId,
                next,
                physicalSizeText,
              );
            }}
          >
            <option value="small">
              Small
            </option>

            <option value="medium">
              Medium
            </option>

            <option value="large">
              Large
            </option>
          </select>
        </label>

      </div>


      {
        selectedType
        && (
          <div className="label">
            Physical package:
            {" "}
            <strong>
              {
                selectedType
                  .package_type
              }
            </strong>
          </div>
        )
      }


      {
        previewing
        && (
          <div className="label">
            Calculating physical profile...
          </div>
        )
      }


      {
        estimate
        && (
          <div
            style={{
              border:
                "1px solid #e5e7eb",

              borderRadius:
                10,

              padding:
                14,

              display:
                "grid",

              gap:
                10,
            }}
          >

            <strong>
              Estimated Physical Profile
            </strong>


            <div className="details-list">

              <div>
                <span className="label">
                  Material
                </span>

                <div>
                  {
                    estimate.material_class
                      ? estimate
                          .material_class
                          .replaceAll(
                            "_",
                            " "
                          )
                      : "-"
                  }
                </div>
              </div>


              <div>
                <span className="label">
                  Estimated Weight Each
                </span>

                <div>
                  {
                    estimate
                      .weight_kg_each
                      .toFixed(2)
                  }
                  {" kg"}
                </div>
              </div>


              <div>
                <span className="label">
                  Estimated Volume Each
                </span>

                <div>
                  {
                    estimate
                      .volume_l_each
                      .toFixed(2)
                  }
                  {" L"}
                </div>
              </div>


              <div>
                <span className="label">
                  Handling Burden
                </span>

                <div>
                  {
                    estimate
                      .handling_score_each
                      .toFixed(2)
                  }
                </div>
              </div>


              <div>
                <span className="label">
                  Fragility
                </span>

                <div>
                  {
                    estimate
                      .fragility_score_each
                      .toFixed(2)
                  }
                </div>
              </div>


              <div>
                <span className="label">
                  Dynamic Load Score Each
                </span>

                <div>
                  {
                    estimate
                      .load_units_each
                      .toFixed(2)
                  }
                </div>
              </div>


              <div>
                <span className="label">
                  Estimate Confidence
                </span>

                <div>
                  {
                    (
                      estimate.confidence
                      * 100
                    ).toFixed(0)
                  }
                  %
                </div>
              </div>


              {
                totalLoadUnits
                != null
                && (
                  <div>
                    <span className="label">
                      Total Cargo Score
                    </span>

                    <div>
                      {
                        totalLoadUnits
                          .toFixed(2)
                      }
                    </div>
                  </div>
                )
              }

            </div>


            {
              estimate.estimation_source
              && (
                <div className="label">
                  Estimate source:
                  {" "}
                  {
                    estimate
                      .estimation_source
                      .replaceAll(
                        "_",
                        " "
                      )
                  }
                </div>
              )
            }

          </div>
        )
      }


      {
        editable
        && (
          <button
            className="btn"

            type="button"

            disabled={
              saving
              || !categoryId
              || !typeId
            }

            onClick={
              saveClassification
            }
          >
            {
              saving
                ? "Saving..."
                : "Save Physical Logistics"
            }
          </button>
        )
      }


      {
        message
        && (
          <div className="notice">
            {message}
          </div>
        )
      }


      {
        error
        && (
          <div className="error">
            {error}
          </div>
        )
      }

    </div>
  );
}
