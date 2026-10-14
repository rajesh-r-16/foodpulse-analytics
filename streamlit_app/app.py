import os
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient
from pymongo.errors import PyMongoError

st.set_page_config(page_title="FoodPulse Analytics", page_icon="🍽️", layout="wide")
ACCENT = "#ff7a18"
COLORS = ["#ff7a18", "#5b68f5", "#14b88a", "#f34f45", "#a66cf5", "#2f91b2", "#f4b23e"]
st.markdown("""
<style>
.stApp{background:#f4f6fa}.block-container{padding-top:1.1rem;padding-bottom:2rem}
.fp-hero{background:linear-gradient(115deg,#202b3a,#102d3c);color:white;border-radius:14px;padding:18px 22px;margin-bottom:15px;border:1px solid #324454}
.fp-hero h1{font-size:1.7rem;margin:0;color:white}.fp-hero p{margin:4px 0 0;color:#d8e1ea;font-size:.88rem}
div[data-testid="stMetric"]{background:white;border:1px solid #e0e5ec;padding:12px 14px;border-radius:12px;box-shadow:0 2px 7px #19233209}
.fp-note{background:white;border:1px solid #e0e5ec;padding:12px 14px;border-radius:10px;min-height:80px}.fp-note small{color:#ff7a18;font-weight:700;text-transform:uppercase}.fp-note p{margin:.3rem 0 0;font-size:.9rem}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def get_client(uri):
    return MongoClient(uri, serverSelectionTimeoutMS=15000, connectTimeoutMS=15000)

def connect_db():
    try:
        uri = st.secrets.get("MONGO_URI", os.getenv("MONGO_URI", ""))
        db_name = st.secrets.get("DB_NAME", os.getenv("DB_NAME", "food_delivery_analytics"))
    except Exception:
        uri = os.getenv("MONGO_URI", "")
        db_name = os.getenv("DB_NAME", "food_delivery_analytics")
    if not uri:
        st.error('MongoDB is not configured. In Streamlit app Settings → Secrets add: MONGO_URI = "your MongoDB Atlas URI"')
        st.stop()
    client = get_client(uri)
    client.admin.command("ping")
    # Use configured DB if it exists; otherwise keep configured name.
    try:
        names = client.list_database_names()
        if db_name not in names:
            candidates = [n for n in names if n not in {"admin", "local", "config"}]
            if candidates:
                db_name = candidates[0]
    except Exception:
        pass
    return client, client[db_name]

def get_collection_df(db, names, limit=20000):
    existing = set(db.list_collection_names())
    for name in names:
        if name in existing:
            docs = list(db[name].find({}, {"_id": 0}).limit(limit))
            return pd.DataFrame(docs), name
    return pd.DataFrame(), names[0]

def alias_columns(df):
    if df.empty: return df
    df = df.copy()
    aliases = {
        "order_id": ["order_id", "orderId"], "customer_id": ["customer_id", "customerId", "user_id"],
        "customer_name": ["customer_name", "customerName", "full_name", "name"],
        "restaurant_id": ["restaurant_id", "restaurantId"], "restaurant_name": ["restaurant_name", "restaurantName"],
        "city": ["city", "delivery_city", "customer_city"], "cuisine": ["cuisine", "cuisine_type"],
        "status": ["status", "order_status", "delivery_status"], "amount": ["amount", "total_amount", "order_amount", "total", "price"],
        "revenue": ["revenue", "net_revenue", "amount", "total_amount", "total"],
        "order_date": ["order_date", "order_datetime", "order_time", "created_at", "date", "timestamp"],
        "delivery_time": ["delivery_time", "delivery_time_min", "duration_minutes", "minutes_taken"],
        "rating": ["rating", "avg_rating", "restaurant_rating", "stars"],
        "payment_method": ["payment_method", "payment", "payment_type"], "device": ["device", "platform", "device_type"],
        "name": ["name", "restaurant_name", "item_name", "full_name"], "price": ["price", "item_price", "unit_price"],
        "category": ["category", "food_category", "type"], "delivery_id": ["delivery_id", "id"],
        "distance_km": ["distance_km", "distance", "delivery_distance_km"], "email": ["email", "customer_email", "email_address"],
    }
    for target, candidates in aliases.items():
        if target not in df.columns:
            for c in candidates:
                if c in df.columns:
                    df[target] = df[c]
                    break
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce", utc=True).dt.tz_convert(None)
    for c in ["amount", "revenue", "price", "rating", "delivery_time", "distance_km"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    if "status" in df.columns: df["status"] = df["status"].astype(str).str.replace("_", " ").str.title()
    return df

def csv_bytes(df):
    return b"" if df is None or df.empty else df.to_csv(index=False).encode("utf-8-sig")

def money(v):
    try: return f"₹{float(v or 0):,.0f}"
    except Exception: return "₹0"

def chart(fig, height=320):
    fig.update_layout(height=height, margin=dict(l=15,r=15,t=48,b=15), paper_bgcolor="white", plot_bgcolor="white", font=dict(color="#465366",size=12), legend=dict(orientation="h",y=1.02,x=0))
    fig.update_xaxes(showgrid=False, linecolor="#e3e7ee"); fig.update_yaxes(gridcolor="#edf0f4")
    return fig

def empty(label): st.info(f"No {label} records found in the connected MongoDB collection. Check the database name or add demo records.")
def note(label, text): st.markdown(f'<div class="fp-note"><small>{label}</small><p>{text}</p></div>', unsafe_allow_html=True)

st.markdown('<div class="fp-hero"><h1>🍽️ Online Food Delivery Analytics</h1><p>FoodPulse Analytics · MongoDB-powered insights, operations and reports</p></div>', unsafe_allow_html=True)
with st.sidebar:
    st.markdown("## 🍽️ FoodPulse")
    st.caption("Analytics & Operations")
    if st.button("🔄 Refresh data", use_container_width=True): st.cache_data.clear(); st.rerun()
    st.divider(); st.caption("Overview · Orders · Restaurants · Customers · Menu · Deliveries · Reports")

try:
    client, db = connect_db()
except Exception as exc:
    st.error("MongoDB connection failed. Check MONGO_URI, database username/password, Atlas Network Access, and the database name.")
    with st.expander("Technical details"): st.code(str(exc))
    st.stop()

@st.cache_data(ttl=60, show_spinner="Loading data from MongoDB Atlas…")
def load_frames(db_name):
    database = get_client(st.secrets.get("MONGO_URI", os.getenv("MONGO_URI", "")))[db_name]
    orders, on = get_collection_df(database, ["orders", "Orders", "food_orders"])
    restaurants, rn = get_collection_df(database, ["restaurants", "Restaurants"])
    customers, cn = get_collection_df(database, ["customers", "Customers", "users"])
    menu, mn = get_collection_df(database, ["menu_items", "menu", "MenuItems", "items"])
    deliveries, dn = get_collection_df(database, ["deliveries", "Deliveries", "delivery_records"])
    reviews, rvn = get_collection_df(database, ["reviews", "ratings", "Reviews"])
    return tuple(alias_columns(x) for x in [orders, restaurants, customers, menu, deliveries, reviews]) + ({"orders":on,"restaurants":rn,"customers":cn,"menu":mn,"deliveries":dn,"reviews":rvn},)

try:
    orders, restaurants, customers, menu, deliveries, reviews, sources = load_frames(db.name)
except Exception as exc:
    st.error("Connected to MongoDB, but could not read collections.")
    with st.expander("Technical details"): st.code(str(exc))
    st.stop()

# Enrich orders with customer names from customer collection where IDs match.
if not customers.empty and "customer_id" in customers.columns and "customer_id" in orders.columns:
    cname = next((c for c in ["customer_name", "name", "full_name"] if c in customers.columns), None)
    if cname:
        lookup = customers.drop_duplicates("customer_id").set_index("customer_id")[cname].to_dict()
        if "customer_name" not in orders.columns: orders["customer_name"] = orders["customer_id"].map(lookup)
        else: orders["customer_name"] = orders["customer_name"].fillna(orders["customer_id"].map(lookup))

with st.expander("🔎 Global filters", expanded=True):
    if not orders.empty and "order_date" in orders.columns and orders.order_date.notna().any():
        mind, maxd = orders.order_date.min().date(), orders.order_date.max().date()
    else: maxd, mind = date.today(), date.today()-timedelta(days=365)
    a,b,c,d = st.columns([1.35,1,1,1])
    dr = a.date_input("Date range", value=(mind,maxd), key="global_dates")
    city_set = set()
    for frame in [orders, restaurants, customers, deliveries]:
        if not frame.empty and "city" in frame.columns: city_set.update(frame.city.dropna().astype(str).tolist())
    cuisine_set = set()
    for frame in [orders, restaurants, menu]:
        if not frame.empty and "cuisine" in frame.columns: cuisine_set.update(frame.cuisine.dropna().astype(str).tolist())
    selected_city = b.selectbox("City", ["All cities"]+sorted(city_set))
    selected_cuisine = c.selectbox("Cuisine", ["All cuisines"]+sorted(cuisine_set))
    d.markdown(" "); d.button("Apply filters", type="primary", use_container_width=True, key="apply_filter_button")
if isinstance(dr,(tuple,list)) and len(dr)==2:
    start, end = pd.Timestamp(dr[0]), pd.Timestamp(dr[1])+pd.Timedelta(days=1)-pd.Timedelta(microseconds=1)
else: start, end = pd.Timestamp(mind), pd.Timestamp(maxd)+pd.Timedelta(days=1)

def filter_frame(frame, date_filter=False):
    out = frame.copy()
    if out.empty: return out
    if date_filter and "order_date" in out.columns: out = out[out.order_date.isna() | ((out.order_date>=start)&(out.order_date<=end))]
    if selected_city!="All cities" and "city" in out.columns: out=out[out.city.astype(str)==selected_city]
    if selected_cuisine!="All cuisines":
        col = "cuisine" if "cuisine" in out.columns else ("category" if "category" in out.columns else None)
        if col: out=out[out[col].astype(str)==selected_cuisine]
    return out
orders_f=filter_frame(orders,True); restaurants_f=filter_frame(restaurants); customers_f=filter_frame(customers); menu_f=filter_frame(menu); deliveries_f=filter_frame(deliveries); reviews_f=filter_frame(reviews)
amount_col = "revenue" if "revenue" in orders_f.columns else "amount"
order_count=len(orders_f); revenue=float(orders_f[amount_col].fillna(0).sum()) if not orders_f.empty and amount_col in orders_f.columns else 0
if not deliveries_f.empty and "delivery_time" in deliveries_f.columns: avg_delivery=deliveries_f.delivery_time.dropna().mean()
elif not orders_f.empty and "delivery_time" in orders_f.columns: avg_delivery=orders_f.delivery_time.dropna().mean()
else: avg_delivery=0
if not restaurants_f.empty and "rating" in restaurants_f.columns: avg_rating=restaurants_f.rating.dropna().mean()
elif not reviews_f.empty and "rating" in reviews_f.columns: avg_rating=reviews_f.rating.dropna().mean()
else: avg_rating=0
cancelled=orders_f.status.str.lower().str.contains("cancel",na=False).sum() if not orders_f.empty and "status" in orders_f.columns else 0
cancel_pct=100*cancelled/order_count if order_count else 0
avg_per_customer=order_count/max(len(customers_f),1) if not customers_f.empty else 0
k=st.columns(6)
k[0].metric("Total orders",f"{order_count:,}"); k[1].metric("Net revenue",money(revenue)); k[2].metric("Avg. delivery",f"{avg_delivery:.1f} min" if pd.notna(avg_delivery) and avg_delivery else "—")
k[3].metric("Avg. rating",f"{avg_rating:.2f}/5" if pd.notna(avg_rating) and avg_rating else "—"); k[4].metric("Cancellations",f"{cancel_pct:.1f}%"); k[5].metric("Orders / customer",f"{avg_per_customer:.1f}" if avg_per_customer else "—")
st.caption(f"Database: `{db.name}` · Orders: `{sources['orders']}` · Restaurants: `{sources['restaurants']}` · Customers: `{sources['customers']}` · Deliveries: `{sources['deliveries']}`")

t_over,t_orders,t_rest,t_custom,t_menu,t_deliv,t_reports,t_explorer=st.tabs(["📊 Overview","🧾 Orders","🍴 Restaurants","👥 Customers","🍱 Menu","🚚 Deliveries","📄 Reports","🗄️ MongoDB Explorer"])

with t_over:
    st.subheader("Business overview")
    x,y,z=st.columns(3)
    with x: note("Peak hour","Order volume by hour highlights busy service windows.")
    with y: note("Top cuisine","Use the cuisine filter to compare restaurant categories.")
    with z: note("Service quality",f"Average delivery time: {avg_delivery:.1f} minutes." if pd.notna(avg_delivery) and avg_delivery else "Add delivery-time data to analyse service quality.")
    l,r=st.columns([1.7,1])
    with l:
        if orders_f.empty: empty("order")
        elif "order_date" in orders_f.columns and orders_f.order_date.notna().any():
            temp=orders_f.dropna(subset=["order_date"]).copy(); temp["month"]=temp.order_date.dt.to_period("M").astype(str)
            agg={"orders":("month","size")}
            if amount_col in temp.columns: agg["revenue"]=(amount_col,"sum")
            monthly=temp.groupby("month",as_index=False).agg(**agg)
            fig=go.Figure(); fig.add_bar(x=monthly.month,y=monthly.orders,name="Orders",marker_color="#ffc58f")
            if "revenue" in monthly.columns: fig.add_trace(go.Scatter(x=monthly.month,y=monthly.revenue,name="Revenue (₹)",mode="lines+markers",yaxis="y2",line=dict(color=ACCENT,width=3))); fig.update_layout(yaxis2=dict(title="Revenue (₹)",overlaying="y",side="right",showgrid=False))
            fig.update_layout(title="Monthly orders & revenue",xaxis_title="Month",yaxis_title="Orders"); st.plotly_chart(chart(fig,350),use_container_width=True)
        elif "status" in orders_f.columns:
            df=orders_f.status.value_counts().rename_axis("Status").reset_index(name="Orders"); st.plotly_chart(chart(px.bar(df,x="Status",y="Orders",title="Orders by status",color="Status",color_discrete_sequence=COLORS)),use_container_width=True)
        else: st.info("Add order_date or status fields to enable this chart.")
    with r:
        if not orders_f.empty:
            pc=next((c for c in ["payment_method","payment_type","payment"] if c in orders_f.columns),None)
            col=pc or ("status" if "status" in orders_f.columns else None)
            if col:
                df=orders_f[col].fillna("Unknown").astype(str).value_counts().rename_axis("Type").reset_index(name="Count")
                st.plotly_chart(chart(px.pie(df,names="Type",values="Count",hole=.6,title="Payment methods" if pc else "Order status mix",color_discrete_sequence=COLORS),350),use_container_width=True)
            else: st.info("Add payment_method or status to show a donut chart.")
        else: empty("order")
    if not orders_f.empty and "city" in orders_f.columns and amount_col in orders_f.columns:
        df=orders_f.groupby("city",as_index=False)[amount_col].sum().sort_values(amount_col,ascending=False).head(10)
        st.plotly_chart(chart(px.bar(df,x="city",y=amount_col,title="Revenue by city",text_auto=".2s",color="city",color_discrete_sequence=COLORS),330),use_container_width=True)
    if not orders_f.empty and "order_date" in orders_f.columns:
        tmp=orders_f.dropna(subset=["order_date"]).copy()
        if not tmp.empty:
            tmp["hour"]=tmp.order_date.dt.hour; hours=tmp.groupby("hour").size().reindex(range(24),fill_value=0).rename("orders").reset_index()
            st.plotly_chart(chart(px.bar(hours,x="hour",y="orders",title="When do customers order?",labels={"hour":"Hour of day","orders":"Orders"},color_discrete_sequence=[ACCENT]),280),use_container_width=True)

with t_orders:
    st.subheader("Order analytics")
    if orders_f.empty: empty("order")
    else:
        l,r=st.columns(2)
        with l:
            if "status" in orders_f.columns:
                df=orders_f.status.value_counts().rename_axis("Status").reset_index(name="Orders"); st.plotly_chart(chart(px.pie(df,names="Status",values="Orders",hole=.55,title="Orders by status",color_discrete_sequence=COLORS)),use_container_width=True)
            if "city" in orders_f.columns and amount_col in orders_f.columns:
                df=orders_f.groupby("city",as_index=False)[amount_col].mean().sort_values(amount_col,ascending=False); st.plotly_chart(chart(px.bar(df,x="city",y=amount_col,title="Average order value by city",color_discrete_sequence=[ACCENT])),use_container_width=True)
        with r:
            if "restaurant_name" in orders_f.columns and amount_col in orders_f.columns:
                df=orders_f.groupby("restaurant_name",as_index=False)[amount_col].sum().nlargest(10,amount_col).sort_values(amount_col); st.plotly_chart(chart(px.bar(df,x=amount_col,y="restaurant_name",orientation="h",title="Top restaurants by order value",color_discrete_sequence=[ACCENT])),use_container_width=True)
            if "device" in orders_f.columns:
                df=orders_f.device.fillna("Unknown").value_counts().rename_axis("Device").reset_index(name="Orders"); st.plotly_chart(chart(px.pie(df,names="Device",values="Orders",hole=.55,title="Orders by device",color_discrete_sequence=COLORS)),use_container_width=True)
        st.dataframe(orders_f,use_container_width=True,hide_index=True); st.download_button("⬇️ Download orders CSV",csv_bytes(orders_f),"foodpulse_orders.csv","text/csv",key="orders_csv")

with t_rest:
    st.subheader("Restaurant performance")
    if restaurants_f.empty: empty("restaurant")
    else:
        l,r=st.columns(2)
        with l:
            if "cuisine" in restaurants_f.columns:
                df=restaurants_f.cuisine.fillna("Unknown").value_counts().rename_axis("Cuisine").reset_index(name="Restaurants"); st.plotly_chart(chart(px.bar(df,x="Cuisine",y="Restaurants",title="Restaurants by cuisine",color_discrete_sequence=[ACCENT])),use_container_width=True)
            if "rating" in restaurants_f.columns: st.plotly_chart(chart(px.histogram(restaurants_f.dropna(subset=["rating"]),x="rating",nbins=10,title="Restaurant rating distribution",color_discrete_sequence=[ACCENT])),use_container_width=True)
        with r:
            namecol="name" if "name" in restaurants_f.columns else ("restaurant_name" if "restaurant_name" in restaurants_f.columns else None)
            if namecol and "rating" in restaurants_f.columns:
                df=restaurants_f.groupby(namecol,as_index=False).rating.mean().nlargest(10,"rating").sort_values("rating"); st.plotly_chart(chart(px.bar(df,x="rating",y=namecol,orientation="h",title="Top rated restaurants",color_discrete_sequence=["#5b68f5"])),use_container_width=True)
            if not orders_f.empty and "restaurant_name" in orders_f.columns and amount_col in orders_f.columns:
                df=orders_f.groupby("restaurant_name",as_index=False)[amount_col].sum().nlargest(10,amount_col).sort_values(amount_col); st.plotly_chart(chart(px.bar(df,x=amount_col,y="restaurant_name",orientation="h",title="Revenue by restaurant",color_discrete_sequence=[ACCENT])),use_container_width=True)
        st.dataframe(restaurants_f,use_container_width=True,hide_index=True); st.download_button("⬇️ Download restaurants CSV",csv_bytes(restaurants_f),"foodpulse_restaurants.csv","text/csv",key="restaurants_csv")

with t_custom:
    st.subheader("Customer insights")
    if customers_f.empty: empty("customer")
    else:
        l,r=st.columns(2)
        with l:
            if "city" in customers_f.columns:
                df=customers_f.city.fillna("Unknown").value_counts().rename_axis("City").reset_index(name="Customers"); st.plotly_chart(chart(px.bar(df,x="City",y="Customers",title="Customers by city",color_discrete_sequence=[ACCENT])),use_container_width=True)
            emailcol=next((c for c in ["email","customer_email"] if c in customers_f.columns),None)
            if emailcol:
                n=customers_f[emailcol].fillna("").astype(str).str.contains("@",regex=False).sum(); df=pd.DataFrame({"Email":["Available","Missing"],"Customers":[n,len(customers_f)-n]}); st.plotly_chart(chart(px.pie(df,names="Email",values="Customers",hole=.55,title="Customer email coverage",color_discrete_sequence=COLORS)),use_container_width=True)
        with r:
            if not orders_f.empty and "customer_id" in orders_f.columns:
                freq=orders_f.groupby("customer_id").size().rename("orders").reset_index(); freq["segment"]=pd.cut(freq.orders,bins=[0,1,3,5,float("inf")],labels=["One-time (1)","Occasional (2–3)","Regular (4–5)","Loyal (6+)"])
                seg=freq.segment.value_counts(sort=False).rename_axis("Segment").reset_index(name="Customers"); st.plotly_chart(chart(px.bar(seg,x="Segment",y="Customers",title="Customer segments by order frequency",color_discrete_sequence=[ACCENT])),use_container_width=True)
                st.markdown("**Most frequent customers**"); st.dataframe(freq.nlargest(10,"orders"),use_container_width=True,hide_index=True)
            else: st.info("Add customer_id to orders to show repeat-customer segments.")
        st.dataframe(customers_f,use_container_width=True,hide_index=True); st.download_button("⬇️ Download customers CSV",csv_bytes(customers_f),"foodpulse_customers.csv","text/csv",key="customers_csv")

with t_menu:
    st.subheader("Menu analytics")
    if menu_f.empty: empty("menu item")
    else:
        l,r=st.columns(2)
        with l:
            catcol="category" if "category" in menu_f.columns else ("cuisine" if "cuisine" in menu_f.columns else None)
            if catcol:
                df=menu_f[catcol].fillna("Unknown").value_counts().rename_axis("Category").reset_index(name="Items"); st.plotly_chart(chart(px.pie(df,names="Category",values="Items",hole=.55,title="Menu items by category",color_discrete_sequence=COLORS)),use_container_width=True)
        with r:
            if "price" in menu_f.columns: st.plotly_chart(chart(px.histogram(menu_f.dropna(subset=["price"]),x="price",nbins=20,title="Menu price distribution",color_discrete_sequence=[ACCENT])),use_container_width=True)
        if "price" in menu_f.columns:
            namecol="name" if "name" in menu_f.columns else menu_f.columns[0]; df=menu_f.nlargest(10,"price").sort_values("price"); st.plotly_chart(chart(px.bar(df,x="price",y=namecol,orientation="h",title="Highest-priced menu items",color_discrete_sequence=[ACCENT])),use_container_width=True)
        st.dataframe(menu_f,use_container_width=True,hide_index=True); st.download_button("⬇️ Download menu CSV",csv_bytes(menu_f),"foodpulse_menu.csv","text/csv",key="menu_csv")

with t_deliv:
    st.subheader("Delivery operations")
    if deliveries_f.empty: empty("delivery")
    else:
        l,r=st.columns(2)
        with l:
            if "status" in deliveries_f.columns:
                df=deliveries_f.status.value_counts().rename_axis("Status").reset_index(name="Deliveries"); st.plotly_chart(chart(px.pie(df,names="Status",values="Deliveries",hole=.55,title="Delivery status distribution",color_discrete_sequence=COLORS)),use_container_width=True)
            if "delivery_time" in deliveries_f.columns: st.plotly_chart(chart(px.histogram(deliveries_f.dropna(subset=["delivery_time"]),x="delivery_time",nbins=18,title="Delivery time distribution (minutes)",color_discrete_sequence=[ACCENT])),use_container_width=True)
        with r:
            if "city" in deliveries_f.columns and "delivery_time" in deliveries_f.columns:
                df=deliveries_f.groupby("city",as_index=False).delivery_time.mean().sort_values("delivery_time",ascending=False); st.plotly_chart(chart(px.bar(df,x="city",y="delivery_time",title="Average delivery time by city",color_discrete_sequence=[ACCENT])),use_container_width=True)
            if "distance_km" in deliveries_f.columns and "delivery_time" in deliveries_f.columns:
                df=deliveries_f.dropna(subset=["distance_km","delivery_time"]).copy()
                if not df.empty:
                    df["distance_band"]=pd.cut(df.distance_km,bins=[-0.01,2,4,6,8,float("inf")],labels=["0–2 km","2–4 km","4–6 km","6–8 km","8+ km"]); agg=df.groupby("distance_band",observed=False,as_index=False).delivery_time.mean(); st.plotly_chart(chart(px.bar(agg,x="distance_band",y="delivery_time",title="Delivery time by distance",color_discrete_sequence=[ACCENT])),use_container_width=True)
        st.markdown("#### Change delivery status")
        idcol=next((c for c in ["delivery_id","order_id","_id"] if c in deliveries.columns),None)
        if idcol and "status" in deliveries.columns:
            editdf=deliveries.copy(); editdf[idcol]=editdf[idcol].astype(str)
            ids=editdf[idcol].tolist()
            def delivery_label(val):
                row=editdf[editdf[idcol]==val].iloc[0]
                order=row.get("order_id",val); return f"{order} · {row.get('status','Unknown')}"
            chosen=st.selectbox("Delivery record",ids,format_func=delivery_label)
            row=editdf[editdf[idcol]==chosen].iloc[0]; options=["Assigned","Picked Up","Out For Delivery","Delivered","Delayed","Cancelled"]
            current=str(row.get("status","Assigned")).title()
            if current not in options: options.insert(0,current)
            with st.form("update_delivery_status"):
                newstatus=st.selectbox("New status",options,index=options.index(current))
                save=st.form_submit_button("Save delivery status",type="primary")
            if save:
                try:
                    collection=db[sources["deliveries"]]; query={idcol:chosen}
                    update={"$set":{"status":newstatus.lower().replace(" ","_"),"updated_at":datetime.utcnow()}}
                    result=collection.update_one(query,update)
                    if result.matched_count==0 and idcol=="_id":
                        from bson import ObjectId
                        try: result=collection.update_one({"_id":ObjectId(chosen)},update)
                        except Exception: pass
                    if result.matched_count:
                        st.success("Delivery status saved to MongoDB."); load_frames.clear(); st.rerun()
                    else: st.error("Delivery not found. Check the identifier field in the deliveries collection.")
                except PyMongoError as exc: st.error("Could not update delivery status."); st.code(str(exc))
        else: st.warning("The deliveries collection needs a delivery_id or order_id field and a status field to enable status changes.")
        st.dataframe(deliveries_f,use_container_width=True,hide_index=True); st.download_button("⬇️ Download deliveries CSV",csv_bytes(deliveries_f),"foodpulse_deliveries.csv","text/csv",key="deliveries_csv")

with t_reports:
    st.subheader("Reports & CSV exports")
    st.caption("Create a filtered order report and open the downloaded CSV in Excel.")
    report=orders.copy(); a,b,c=st.columns(3)
    statuses=sorted(report.status.dropna().astype(str).unique()) if not report.empty and "status" in report.columns else []
    restaurants_list=sorted(report.restaurant_name.dropna().astype(str).unique()) if not report.empty and "restaurant_name" in report.columns else []
    cities=sorted(report.city.dropna().astype(str).unique()) if not report.empty and "city" in report.columns else []
    rs=a.selectbox("Order status",["All statuses"]+statuses); rr=b.selectbox("Restaurant",["All restaurants"]+restaurants_list); rc=c.selectbox("City",["All cities"]+cities)
    if not report.empty:
        if "order_date" in report.columns: report=report[report.order_date.isna()|((report.order_date>=start)&(report.order_date<=end))]
        if rs!="All statuses" and "status" in report.columns: report=report[report.status.astype(str)==rs]
        if rr!="All restaurants" and "restaurant_name" in report.columns: report=report[report.restaurant_name.astype(str)==rr]
        if rc!="All cities" and "city" in report.columns: report=report[report.city.astype(str)==rc]
    ra="revenue" if "revenue" in report.columns else "amount"
    c1,c2,c3=st.columns(3); c1.metric("Report rows",f"{len(report):,}"); c2.metric("Report revenue",money(report[ra].fillna(0).sum()) if not report.empty and ra in report.columns else "₹0"); c3.metric("Average order value",money(report[ra].mean()) if not report.empty and ra in report.columns else "₹0")
    st.dataframe(report,use_container_width=True,hide_index=True)
    st.download_button("⬇️ Download filtered report CSV",csv_bytes(report),f"foodpulse_report_{date.today().isoformat()}.csv","text/csv",type="primary",key="report_csv")
    a,b,c=st.columns(3); a.download_button("Customers CSV",csv_bytes(customers_f),"foodpulse_customers.csv","text/csv",key="report_customers_csv"); b.download_button("Restaurants CSV",csv_bytes(restaurants_f),"foodpulse_restaurants.csv","text/csv",key="report_restaurants_csv"); c.download_button("Deliveries CSV",csv_bytes(deliveries_f),"foodpulse_deliveries.csv","text/csv",key="report_deliveries_csv")

with t_explorer:
    st.subheader("MongoDB Explorer")
    st.caption("Inspect collection names, document counts and sample documents from your connected database.")
    try:
        names=sorted(n for n in db.list_collection_names() if not n.startswith("system."))
        if not names: st.info("No collections found in this database. Verify DB_NAME or seed the demo data.")
        else:
            selected=st.selectbox("Collection",names); coll=db[selected]; a,b=st.columns(2); a.metric("Documents",f"{coll.count_documents({}):,}"); b.metric("Collection",selected)
            sample=list(coll.find({}, {"_id":0}).limit(200))
            if sample:
                frame=pd.DataFrame(sample); st.dataframe(frame,use_container_width=True,hide_index=True); st.download_button(f"⬇️ Download {selected} CSV",csv_bytes(frame),f"{selected}.csv","text/csv",key=f"explorer_{selected}")
            else: st.info("This collection is empty.")
    except PyMongoError as exc: st.error("Could not read MongoDB collection."); st.code(str(exc))

st.divider(); st.caption("FoodPulse Analytics · Streamlit + MongoDB Atlas · Use synthetic/demo data for presentations.")
