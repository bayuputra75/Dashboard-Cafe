# Jalankan dengan: streamlit run app_cafe.py
# Pastikan file cafe_sales.xlsx berada di folder yang sama dengan app_cafe.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Dashboard Penjualan Kafe",
    layout="wide"
)

HARI_ID = {
    "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
    "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
}
URUTAN_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
NILAI_RUSAK = ["ERROR", "UNKNOWN", ""]


# Pembacaan dan pembersihan data
@st.cache_data
def load_data():
    df = pd.read_excel("cafe_sales.xlsx", dtype=str)
    df.columns = df.columns.str.strip()

    # Ubah teks ERROR, UNKNOWN, dan spasi kosong menjadi nilai kosong (NA)
    for col in df.columns:
        df[col] = df[col].str.strip()
        df[col] = df[col].mask(df[col].isin(NILAI_RUSAK))

    # Hapus transaksi ganda berdasarkan ID
    df = df.drop_duplicates(subset="Transaction ID")

    # Konversi kolom numerik
    for col in ["Quantity", "Price Per Unit", "Total Spent"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Isi nilai yang kosong dengan hitungan dari kolom lain
    df["Price Per Unit"] = df["Price Per Unit"].fillna(df["Total Spent"] / df["Quantity"])
    df["Quantity"] = df["Quantity"].fillna(df["Total Spent"] / df["Price Per Unit"])
    df["Total Spent"] = df["Total Spent"].fillna(df["Quantity"] * df["Price Per Unit"])

    # Konversi tanggal
    df["Transaction Date"] = pd.to_datetime(df["Transaction Date"], errors="coerce")

    # Buang baris yang nilai utamanya tetap tidak bisa diselamatkan
    df = df.dropna(subset=["Quantity", "Total Spent", "Transaction Date"])

    # Ganti nama kolom ke bahasa Indonesia
    df = df.rename(columns={
        "Transaction ID": "ID_Transaksi",
        "Item": "Produk",
        "Quantity": "Jumlah",
        "Price Per Unit": "Harga_Satuan",
        "Total Spent": "Total_Penjualan",
        "Payment Method": "Metode_Pembayaran",
        "Location": "Lokasi",
        "Transaction Date": "Tanggal",
    })

    # Isi kolom kategori yang kosong
    df["Produk"] = df["Produk"].fillna("Tidak Diketahui")
    df["Metode_Pembayaran"] = df["Metode_Pembayaran"].fillna("Tidak Diketahui")
    df["Lokasi"] = df["Lokasi"].fillna("Tidak Diketahui")

    # Kolom turunan untuk grafik
    df["Jumlah"] = df["Jumlah"].astype(int)
    df["Bulan"] = df["Tanggal"].dt.to_period("M").astype(str)
    df["Hari"] = df["Tanggal"].dt.day_name().map(HARI_ID)

    return df.reset_index(drop=True)


df = load_data()

# Judul dan deskripsi
st.title("Dashboard Penjualan Kafe")
st.markdown(
    "Dashboard ini membantu memantau penjualan kopi, teh, jus, smoothie, kue, kue kering, "
    "sandwich, dan salad selama tahun 2023. Lihat produk terlaris, metode pembayaran yang "
    "paling sering dipakai pelanggan, serta perbandingan transaksi di tempat (In-store) "
    "dan takeaway."
)

# Filter di sidebar
st.sidebar.header("Filter Dashboard")

min_date = df["Tanggal"].min().date()
max_date = df["Tanggal"].max().date()
date_range = st.sidebar.date_input(
    "Periode",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

produk_options = sorted(df["Produk"].unique())
produk_terpilih = st.sidebar.multiselect(
    "Produk",
    produk_options,
    default=produk_options
)

lokasi_options = sorted(df["Lokasi"].unique())
lokasi_terpilih = st.sidebar.multiselect(
    "Lokasi",
    lokasi_options,
    default=lokasi_options
)

pembayaran_options = sorted(df["Metode_Pembayaran"].unique())
pembayaran_terpilih = st.sidebar.multiselect(
    "Metode Pembayaran",
    pembayaran_options,
    default=pembayaran_options
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, tuple) and len(date_range) == 1:
    start_date = end_date = date_range[0]
else:
    start_date = end_date = date_range

st.sidebar.info(
    f"Menampilkan {len(produk_terpilih)} produk dan {len(lokasi_terpilih)} lokasi terpilih."
)

# Terapkan filter
filtered = df[
    (df["Tanggal"] >= pd.to_datetime(start_date)) &
    (df["Tanggal"] <= pd.to_datetime(end_date)) &
    (df["Produk"].isin(produk_terpilih)) &
    (df["Lokasi"].isin(lokasi_terpilih)) &
    (df["Metode_Pembayaran"].isin(pembayaran_terpilih))
].copy()

if filtered.empty:
    st.warning("Tidak ada data yang cocok dengan filter yang dipilih.")
    st.stop()

# KPI
total_sales = filtered["Total_Penjualan"].sum()
total_transaksi = filtered["ID_Transaksi"].nunique()
total_item = filtered["Jumlah"].sum()
avg_transaksi = total_sales / total_transaksi
produk_terlaris = filtered.groupby("Produk")["Jumlah"].sum().idxmax()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Penjualan", f"${total_sales:,.2f}")
k2.metric("Jumlah Transaksi", f"{total_transaksi:,}")
k3.metric("Item Terjual", f"{total_item:,}")
k4.metric("Rata-rata per Transaksi", f"${avg_transaksi:,.2f}")
k5.metric("Produk Terlaris", produk_terlaris)

# Grafik 1: Line chart tren penjualan bulanan
monthly = (
    filtered.groupby("Bulan", as_index=False)["Total_Penjualan"]
    .sum()
)
fig = px.line(
    monthly,
    x="Bulan",
    y="Total_Penjualan",
    markers=True,
    title="Tren Penjualan Bulanan"
)
fig.update_layout(yaxis_title="Penjualan ($)", xaxis_title="")
st.plotly_chart(fig, width="stretch")

# Baris 2: Bar chart produk dan pie chart metode pembayaran
col1, col2 = st.columns(2)

# Grafik 2: Bar chart penjualan per produk
product_sales = (
    filtered.groupby("Produk", as_index=False)["Total_Penjualan"]
    .sum()
    .sort_values("Total_Penjualan", ascending=False)
)
fig = px.bar(
    product_sales,
    x="Produk",
    y="Total_Penjualan",
    title="Penjualan Berdasarkan Produk",
    text_auto=".2s",
    color="Produk"
)
fig.update_layout(yaxis_title="Penjualan ($)", xaxis_title="", showlegend=False)
col1.plotly_chart(fig, width="stretch")

# Grafik 3: Pie chart metode pembayaran
payment_sales = (
    filtered.groupby("Metode_Pembayaran", as_index=False)["Total_Penjualan"]
    .sum()
)
fig = px.pie(
    payment_sales,
    names="Metode_Pembayaran",
    values="Total_Penjualan",
    title="Kontribusi Metode Pembayaran",
    hole=0.45
)
col2.plotly_chart(fig, width="stretch")

# Baris 3: Pie chart lokasi dan histogram nilai transaksi
col3, col4 = st.columns(2)

# Grafik 4: Pie chart lokasi
location_sales = (
    filtered.groupby("Lokasi", as_index=False)["Total_Penjualan"]
    .sum()
)
fig = px.pie(
    location_sales,
    names="Lokasi",
    values="Total_Penjualan",
    title="Kontribusi Penjualan per Lokasi",
    hole=0.45
)
col3.plotly_chart(fig, width="stretch")

# Grafik 5: Histogram distribusi nilai transaksi (rentang $5 agar tidak ada celah)
fig = px.histogram(
    filtered,
    x="Total_Penjualan",
    title="Distribusi Nilai Transaksi"
)
fig.update_traces(xbins=dict(start=0, end=30, size=5))
fig.update_layout(xaxis_title="Total per Transaksi ($)", yaxis_title="Jumlah Transaksi", bargap=0.05)
col4.plotly_chart(fig, width="stretch")



# Baris 4: Bar chart penjualan per hari dan item terjual per produk
col5, col6 = st.columns(2)

# Grafik 6: Bar chart penjualan per hari dalam seminggu
day_sales = (
    filtered.groupby("Hari", as_index=False)["Total_Penjualan"]
    .sum()
    .set_index("Hari")
    .reindex(URUTAN_HARI)
    .reset_index()
)
fig = px.bar(
    day_sales,
    x="Hari",
    y="Total_Penjualan",
    title="Penjualan per Hari dalam Seminggu",
    text_auto=".2s"
)
fig.update_layout(yaxis_title="Penjualan ($)", xaxis_title="")
col5.plotly_chart(fig, width="stretch")

# Grafik 7: Bar chart jumlah item terjual per produk
item_sales = (
    filtered.groupby("Produk", as_index=False)["Jumlah"]
    .sum()
    .sort_values("Jumlah", ascending=True)
)
fig = px.bar(
    item_sales,
    x="Jumlah",
    y="Produk",
    orientation="h",
    title="Jumlah Item Terjual per Produk",
    text_auto=True
)
fig.update_layout(xaxis_title="Item Terjual", yaxis_title="")
col6.plotly_chart(fig, width="stretch")

# Tabel detail transaksi
st.subheader("Detail Transaksi")
display_df = filtered.sort_values("Tanggal", ascending=False)
st.dataframe(
    display_df[[
        "ID_Transaksi", "Tanggal", "Produk", "Jumlah",
        "Harga_Satuan", "Total_Penjualan", "Metode_Pembayaran", "Lokasi"
    ]],
    width="stretch",
    hide_index=True,
    column_config={
        "Tanggal": st.column_config.DateColumn("Tanggal", format="DD-MM-YYYY"),
        "Harga_Satuan": st.column_config.NumberColumn("Harga Satuan", format="$ %.2f"),
        "Total_Penjualan": st.column_config.NumberColumn("Total Penjualan", format="$ %.2f"),
    }
)

# Tombol download
csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Data Hasil Filter",
    data=csv,
    file_name="data_penjualan_kafe_filtered.csv",
    mime="text/csv"
)

st.caption(
    f"Menampilkan {len(filtered):,} transaksi dari total {len(df):,} transaksi yang sudah dibersihkan."
)