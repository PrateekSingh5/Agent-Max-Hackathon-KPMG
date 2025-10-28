--
-- PostgreSQL database dump
--

\restrict 2HpOzpabsgYgHse0PdELViK9WYa0UkEFDDJ3tOt4vDasGnVCETuuZ87CNNDi7Z5

-- Dumped from database version 18.0 (Debian 18.0-1.pgdg13+3)
-- Dumped by pg_dump version 18.0 (Debian 18.0-1.pgdg13+3)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: employees; Type: TABLE; Schema: public; Owner: myuser
--

CREATE TABLE public.employees (
    employee_id character varying(32) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    email character varying(320) NOT NULL,
    department character varying(120) NOT NULL,
    cost_center character varying(50) NOT NULL,
    grade character varying(20) NOT NULL,
    hire_date date NOT NULL,
    is_active boolean NOT NULL,
    corporate_card boolean NOT NULL,
    manager_id character varying(32) NOT NULL,
    access_label character(1)
);


ALTER TABLE public.employees OWNER TO myuser;

--
-- Name: expense_claims; Type: TABLE; Schema: public; Owner: myuser
--

CREATE TABLE public.expense_claims (
    id integer NOT NULL,
    claim_id character varying(30) NOT NULL,
    employee_id character varying(32) NOT NULL,
    claim_date date NOT NULL,
    expense_category character varying(100) NOT NULL,
    amount numeric(12,2) NOT NULL,
    currency character varying(10) NOT NULL,
    vendor_name character varying(255),
    linked_booking_id character varying(50),
    receipt_id character varying(50),
    payment_mode character varying(30),
    status character varying(30),
    details text,
    others_1 text,
    others_2 text,
    auto_approved boolean NOT NULL,
    is_duplicate boolean NOT NULL,
    fraud_flag boolean NOT NULL
);


ALTER TABLE public.expense_claims OWNER TO myuser;

--
-- Name: expense_claims_id_seq; Type: SEQUENCE; Schema: public; Owner: myuser
--

CREATE SEQUENCE public.expense_claims_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.expense_claims_id_seq OWNER TO myuser;

--
-- Name: expense_claims_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: myuser
--

ALTER SEQUENCE public.expense_claims_id_seq OWNED BY public.expense_claims.id;


--
-- Name: expense_policies; Type: TABLE; Schema: public; Owner: myuser
--

CREATE TABLE public.expense_policies (
    id integer NOT NULL,
    policy_id character varying(20) NOT NULL,
    category character varying(100) NOT NULL,
    max_allowance numeric(10,2) NOT NULL,
    per_diem numeric(10,2) NOT NULL,
    applicable_grades character varying(100) NOT NULL,
    notes text
);


ALTER TABLE public.expense_policies OWNER TO myuser;

--
-- Name: expense_policies_id_seq; Type: SEQUENCE; Schema: public; Owner: myuser
--

CREATE SEQUENCE public.expense_policies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.expense_policies_id_seq OWNER TO myuser;

--
-- Name: expense_policies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: myuser
--

ALTER SEQUENCE public.expense_policies_id_seq OWNED BY public.expense_policies.id;


--
-- Name: expense_validation_logs; Type: TABLE; Schema: public; Owner: myuser
--

CREATE TABLE public.expense_validation_logs (
    log_id bigint NOT NULL,
    claim_id character varying(32) NOT NULL,
    employee_id character varying(32) NOT NULL,
    status_val character varying(64) NOT NULL,
    payment_mode character varying(64),
    auto_approved boolean DEFAULT false,
    raw_validation_json jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.expense_validation_logs OWNER TO myuser;

--
-- Name: expense_validation_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: myuser
--

CREATE SEQUENCE public.expense_validation_logs_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.expense_validation_logs_log_id_seq OWNER TO myuser;

--
-- Name: expense_validation_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: myuser
--

ALTER SEQUENCE public.expense_validation_logs_log_id_seq OWNED BY public.expense_validation_logs.log_id;


--
-- Name: per_diem_rates; Type: TABLE; Schema: public; Owner: myuser
--

CREATE TABLE public.per_diem_rates (
    id integer NOT NULL,
    location text NOT NULL,
    currency character varying(10) NOT NULL,
    per_diem_rate numeric(10,2) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.per_diem_rates OWNER TO myuser;

--
-- Name: per_diem_rates_id_seq; Type: SEQUENCE; Schema: public; Owner: myuser
--

CREATE SEQUENCE public.per_diem_rates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.per_diem_rates_id_seq OWNER TO myuser;

--
-- Name: per_diem_rates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: myuser
--

ALTER SEQUENCE public.per_diem_rates_id_seq OWNED BY public.per_diem_rates.id;


--
-- Name: reimbursement_accounts; Type: TABLE; Schema: public; Owner: myuser
--

CREATE TABLE public.reimbursement_accounts (
    id integer NOT NULL,
    bank_account_id character varying(20) NOT NULL,
    employee_id character varying(32) NOT NULL,
    bank_name character varying(100) NOT NULL,
    account_number_masked character varying(30) NOT NULL,
    ifsc character varying(15) NOT NULL
);


ALTER TABLE public.reimbursement_accounts OWNER TO myuser;

--
-- Name: reimbursement_accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: myuser
--

CREATE SEQUENCE public.reimbursement_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reimbursement_accounts_id_seq OWNER TO myuser;

--
-- Name: reimbursement_accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: myuser
--

ALTER SEQUENCE public.reimbursement_accounts_id_seq OWNED BY public.reimbursement_accounts.id;


--
-- Name: vendors; Type: TABLE; Schema: public; Owner: myuser
--

CREATE TABLE public.vendors (
    id integer NOT NULL,
    vendor_id character varying(20) NOT NULL,
    vendor_name character varying(200) NOT NULL,
    category character varying(100) NOT NULL,
    country character varying(100) NOT NULL,
    contract_rate_reference numeric(10,2),
    vendor_verified boolean NOT NULL
);


ALTER TABLE public.vendors OWNER TO myuser;

--
-- Name: vendors_id_seq; Type: SEQUENCE; Schema: public; Owner: myuser
--

CREATE SEQUENCE public.vendors_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vendors_id_seq OWNER TO myuser;

--
-- Name: vendors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: myuser
--

ALTER SEQUENCE public.vendors_id_seq OWNED BY public.vendors.id;


--
-- Name: expense_claims id; Type: DEFAULT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_claims ALTER COLUMN id SET DEFAULT nextval('public.expense_claims_id_seq'::regclass);


--
-- Name: expense_policies id; Type: DEFAULT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_policies ALTER COLUMN id SET DEFAULT nextval('public.expense_policies_id_seq'::regclass);


--
-- Name: expense_validation_logs log_id; Type: DEFAULT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_validation_logs ALTER COLUMN log_id SET DEFAULT nextval('public.expense_validation_logs_log_id_seq'::regclass);


--
-- Name: per_diem_rates id; Type: DEFAULT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.per_diem_rates ALTER COLUMN id SET DEFAULT nextval('public.per_diem_rates_id_seq'::regclass);


--
-- Name: reimbursement_accounts id; Type: DEFAULT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.reimbursement_accounts ALTER COLUMN id SET DEFAULT nextval('public.reimbursement_accounts_id_seq'::regclass);


--
-- Name: vendors id; Type: DEFAULT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.vendors ALTER COLUMN id SET DEFAULT nextval('public.vendors_id_seq'::regclass);


--
-- Data for Name: employees; Type: TABLE DATA; Schema: public; Owner: myuser
--

COPY public.employees (employee_id, first_name, last_name, email, department, cost_center, grade, hire_date, is_active, corporate_card, manager_id, access_label) FROM stdin;
E1004	Isha	Verma	isha.verma4@company.com	Sales	CC105	G3	2023-01-11	t	f	E1106	M
E1000	Vivaan	Sharma	vivaan.sharma0@company.com	Engineering	CC102	G1	2023-07-17	t	t	E1070	E
E1001	Diya	Mehta	diya.mehta1@company.com	Sales	CC103	G2	2022-11-10	t	t	E1106	E
E1002	Kavya	Gupta	kavya.gupta2@company.com	HR	CC103	G4	2024-08-04	t	f	E1051	E
E1003	Aarav	Patel	aarav.patel3@company.com	Finance	CC104	G2	2024-09-22	t	t	E1213	E
E1005	Aarav	Nair	aarav.nair5@company.com	HR	CC101	G5	2024-04-10	t	f	E1139	E
E1006	Diya	Singh	diya.singh6@company.com	Sales	CC100	G2	2024-05-22	t	f	E1185	E
E1007	Vivaan	Gupta	vivaan.gupta7@company.com	Finance	CC107	G3	2023-01-20	t	t	E1220	E
E1008	Isha	Singh	isha.singh8@company.com	Sales	CC109	G2	2023-05-11	t	t	E1297	E
E1009	Aditya	Nair	aditya.nair9@company.com	Operations	CC103	G3	2023-11-01	t	t	E1147	E
E1010	Vihaan	Sharma	vihaan.sharma10@company.com	Finance	CC101	G2	2023-08-28	t	f	E1275	E
E1077	Diya	Agarwal	diya.agarwal77@company.com	Sales	CC106	G2	2024-08-17	t	f	E1095	E
E1079	Isha	Mehta	isha.mehta79@company.com	Finance	CC101	G4	2023-07-20	t	t	E1095	E
E1081	Vihaan	Sharma	vihaan.sharma81@company.com	Engineering	CC102	G4	2024-07-06	t	t	E1004	E
E1082	Diya	Gupta	diya.gupta82@company.com	Finance	CC102	G5	2024-01-28	t	t	E1027	E
E1083	Aditya	Kumar	aditya.kumar83@company.com	Sales	CC104	G5	2023-01-27	t	f	E1078	E
E1084	Ananya	Gupta	ananya.gupta84@company.com	Engineering	CC101	G3	2022-12-25	t	t	E1029	E
E1085	Diya	Sharma	diya.sharma85@company.com	HR	CC105	G1	2023-09-29	t	f	E1242	E
E1086	Aarav	Mehta	aarav.mehta86@company.com	HR	CC105	G4	2024-02-22	t	t	E1191	E
E1087	Ananya	Patel	ananya.patel87@company.com	Finance	CC109	G5	2024-03-26	t	f	E1059	E
E1089	Saanvi	Gupta	saanvi.gupta89@company.com	Operations	CC106	G3	2024-01-27	t	t	E1297	E
E1091	Arjun	Agarwal	arjun.agarwal91@company.com	Operations	CC100	G5	2024-09-26	t	t	E1167	E
E1092	Vivaan	Gupta	vivaan.gupta92@company.com	Operations	CC103	G4	2023-11-29	t	f	E1213	E
E1153	Isha	Verma	isha.verma153@company.com	Operations	CC105	G1	2024-09-10	t	f	E1058	E
E1154	Arjun	Gupta	arjun.gupta154@company.com	Sales	CC103	G5	2023-02-11	t	t	E1139	E
E1155	Aarav	Singh	aarav.singh155@company.com	Operations	CC103	G1	2023-06-15	t	t	E1058	E
E1156	Diya	Gupta	diya.gupta156@company.com	Engineering	CC109	G1	2023-06-04	t	f	E1110	E
E1157	Aditya	Patel	aditya.patel157@company.com	Engineering	CC101	G1	2024-04-14	t	t	E1029	E
E1158	Aarav	Singh	aarav.singh158@company.com	Finance	CC100	G2	2023-06-09	t	f	E1189	E
E1159	Aarav	Patel	aarav.patel159@company.com	Sales	CC101	G4	2023-12-14	t	f	E1058	E
E1160	Isha	Reddy	isha.reddy160@company.com	HR	CC108	G2	2024-06-07	t	t	E1299	E
E1161	Kavya	Kumar	kavya.kumar161@company.com	Sales	CC100	G4	2024-01-21	t	f	E1073	E
E1162	Ananya	Verma	ananya.verma162@company.com	Sales	CC101	G3	2024-02-23	t	t	E1139	E
E1163	Vivaan	Patel	vivaan.patel163@company.com	Operations	CC108	G3	2023-07-17	t	f	E1078	E
E1165	Vivaan	Reddy	vivaan.reddy165@company.com	HR	CC103	G4	2023-05-17	t	f	E1080	E
E1011	Vihaan	Nair	vihaan.nair11@company.com	HR	CC102	G3	2023-11-18	t	t	E1228	M
E1012	Vihaan	Reddy	vihaan.reddy12@company.com	Operations	CC106	G5	2024-04-12	t	f	E1228	M
E1018	Aditya	Singh	aditya.singh18@company.com	Operations	CC100	G5	2023-03-23	t	f	E1105	M
E1027	Vivaan	Mehta	vivaan.mehta27@company.com	HR	CC107	G1	2023-10-06	t	t	E1147	M
E1029	Aditya	Mehta	aditya.mehta29@company.com	HR	CC103	G1	2023-04-14	t	f	E1018	M
E1051	Aarav	Nair	aarav.nair51@company.com	HR	CC105	G3	2023-05-24	t	t	E1191	M
E1230	Saanvi	Agarwal	saanvi.agarwal230@company.com	HR	CC105	G4	2023-12-19	t	t	E1106	E
E1231	Isha	Agarwal	isha.agarwal231@company.com	Sales	CC101	G4	2023-12-28	t	f	E1191	E
E1232	Kavya	Patel	kavya.patel232@company.com	Operations	CC107	G1	2022-11-09	t	t	E1213	E
E1233	Vivaan	Gupta	vivaan.gupta233@company.com	Finance	CC106	G5	2024-07-30	t	t	E1189	E
E1234	Diya	Patel	diya.patel234@company.com	Finance	CC105	G4	2024-09-03	t	t	E1297	E
E1235	Diya	Patel	diya.patel235@company.com	HR	CC105	G3	2024-04-03	t	t	E1275	E
E1236	Vivaan	Sharma	vivaan.sharma236@company.com	Operations	CC106	G5	2023-04-17	t	t	E1221	E
E1237	Arjun	Kumar	arjun.kumar237@company.com	Engineering	CC109	G3	2024-09-28	t	f	E1122	E
E1058	Kavya	Kumar	kavya.kumar58@company.com	Finance	CC106	G3	2024-08-21	t	t	E1176	M
E1059	Vihaan	Mehta	vihaan.mehta59@company.com	Engineering	CC109	G5	2024-08-19	t	f	E1080	M
E1070	Saanvi	Verma	saanvi.verma70@company.com	Engineering	CC104	G3	2024-10-08	t	f	E1051	M
E1073	Vihaan	Mehta	vihaan.mehta73@company.com	Sales	CC109	G4	2023-11-11	t	f	E1275	M
E1078	Aditya	Sharma	aditya.sharma78@company.com	Finance	CC103	G4	2023-07-02	t	f	E1027	M
E1080	Kavya	Sharma	kavya.sharma80@company.com	Sales	CC100	G1	2023-10-02	t	t	E1080	M
E1088	Saanvi	Mehta	saanvi.mehta88@company.com	Finance	CC103	G1	2024-06-06	t	f	E1122	M
E1090	Saanvi	Singh	saanvi.singh90@company.com	Engineering	CC105	G3	2023-04-13	t	f	E1029	M
E1095	Isha	Nair	isha.nair95@company.com	Finance	CC103	G1	2023-07-13	t	t	E1147	M
E1105	Vihaan	Gupta	vihaan.gupta105@company.com	Engineering	CC103	G2	2023-07-06	t	t	E1105	M
E1106	Aditya	Sharma	aditya.sharma106@company.com	Operations	CC107	G3	2023-12-01	t	t	E1059	M
E1110	Saanvi	Verma	saanvi.verma110@company.com	HR	CC104	G5	2024-01-31	t	f	E1297	M
E1122	Saanvi	Gupta	saanvi.gupta122@company.com	Engineering	CC106	G2	2024-01-19	t	t	E1213	M
E1123	Vivaan	Kumar	vivaan.kumar123@company.com	Operations	CC104	G1	2023-12-07	t	f	E1088	M
E1127	Ananya	Mehta	ananya.mehta127@company.com	Engineering	CC107	G1	2024-08-18	t	t	E1059	M
E1139	Vihaan	Mehta	vihaan.mehta139@company.com	Operations	CC104	G3	2024-05-16	t	t	E1051	M
E1147	Arjun	Agarwal	arjun.agarwal147@company.com	Finance	CC101	G2	2023-11-03	t	f	E1185	M
E1164	Diya	Reddy	diya.reddy164@company.com	Operations	CC109	G4	2023-08-06	t	t	E1070	M
E1167	Isha	Patel	isha.patel167@company.com	Sales	CC101	G1	2024-09-11	t	t	E1018	M
E1176	Arjun	Singh	arjun.singh176@company.com	Sales	CC100	G2	2024-05-12	t	t	E1251	M
E1184	Diya	Mehta	diya.mehta184@company.com	HR	CC104	G1	2024-05-18	t	f	E1139	M
E1185	Aarav	Singh	aarav.singh185@company.com	HR	CC105	G1	2023-04-02	t	f	E1027	M
E1189	Aditya	Kumar	aditya.kumar189@company.com	Operations	CC102	G1	2023-04-29	t	t	E1297	M
E1191	Isha	Patel	isha.patel191@company.com	HR	CC107	G3	2024-01-02	t	f	E1095	M
E1213	Aarav	Singh	aarav.singh213@company.com	Finance	CC102	G2	2023-01-18	t	t	E1011	M
E1217	Diya	Nair	diya.nair217@company.com	HR	CC109	G5	2022-12-12	t	t	E1184	M
E1220	Kavya	Reddy	kavya.reddy220@company.com	Operations	CC100	G4	2024-03-11	t	f	E1266	M
E1221	Aarav	Mehta	aarav.mehta221@company.com	Sales	CC105	G1	2023-10-26	t	f	E1275	M
E1228	Kavya	Kumar	kavya.kumar228@company.com	Sales	CC106	G5	2023-01-01	t	t	E1059	M
E1229	Kavya	Kumar	kavya.kumar229@company.com	Sales	CC105	G3	2023-09-02	t	f	E1185	M
E1242	Kavya	Patel	kavya.patel242@company.com	Sales	CC104	G4	2024-06-26	t	f	E1229	M
E1248	Kavya	Patel	kavya.patel248@company.com	Engineering	CC102	G5	2024-06-06	t	f	E1191	M
E1251	Arjun	Nair	arjun.nair251@company.com	Finance	CC107	G1	2023-06-16	t	t	E1191	M
E1266	Diya	Kumar	diya.kumar266@company.com	Operations	CC108	G5	2024-06-07	t	f	E1070	M
E1275	Arjun	Kumar	arjun.kumar275@company.com	HR	CC105	G4	2024-09-29	t	f	E1299	M
E1293	Aditya	Nair	aditya.nair293@company.com	HR	CC108	G4	2024-06-20	t	t	E1228	M
E1297	Vivaan	Reddy	vivaan.reddy297@company.com	HR	CC102	G5	2024-01-08	t	f	E1018	M
E1299	Arjun	Sharma	arjun.sharma299@company.com	Sales	CC100	G4	2023-05-20	t	f	E1105	M
F3094	Finance	Team	finance.team@company.com	Finance	FC121	F1	2020-07-12	t	t	F3094	F
E1013	Isha	Gupta	isha.gupta13@company.com	HR	CC101	G1	2023-02-27	t	t	E1297	E
E1014	Aditya	Patel	aditya.patel14@company.com	Operations	CC101	G4	2024-09-04	t	f	E1012	E
E1015	Diya	Nair	diya.nair15@company.com	Operations	CC100	G1	2024-04-02	t	f	E1105	E
E1016	Isha	Verma	isha.verma16@company.com	Engineering	CC107	G1	2023-08-05	t	f	E1293	E
E1017	Kavya	Patel	kavya.patel17@company.com	Finance	CC108	G5	2024-03-11	t	t	E1105	E
E1019	Saanvi	Sharma	saanvi.sharma19@company.com	Finance	CC103	G1	2023-01-31	t	t	E1127	E
E1020	Diya	Verma	diya.verma20@company.com	Sales	CC108	G2	2023-01-04	t	t	E1004	E
E1021	Saanvi	Reddy	saanvi.reddy21@company.com	Operations	CC109	G4	2023-03-27	t	t	E1191	E
E1022	Kavya	Gupta	kavya.gupta22@company.com	HR	CC105	G4	2024-10-08	t	f	E1051	E
E1023	Vivaan	Gupta	vivaan.gupta23@company.com	Finance	CC100	G5	2023-05-27	t	t	E1275	E
E1024	Diya	Gupta	diya.gupta24@company.com	Sales	CC103	G1	2022-10-16	t	t	E1228	E
E1025	Isha	Verma	isha.verma25@company.com	Finance	CC107	G2	2024-03-18	t	t	E1251	E
E1026	Diya	Agarwal	diya.agarwal26@company.com	HR	CC106	G2	2024-02-05	t	t	E1073	E
E1028	Aarav	Mehta	aarav.mehta28@company.com	Engineering	CC103	G2	2023-09-21	t	f	E1051	E
E1030	Kavya	Verma	kavya.verma30@company.com	Operations	CC100	G1	2022-11-29	t	t	E1059	E
E1031	Aditya	Mehta	aditya.mehta31@company.com	Engineering	CC106	G1	2024-02-18	t	t	E1275	E
E1032	Ananya	Sharma	ananya.sharma32@company.com	HR	CC104	G4	2023-11-12	t	f	E1122	E
E1033	Aditya	Gupta	aditya.gupta33@company.com	Sales	CC109	G5	2023-08-08	t	t	E1189	E
E1034	Isha	Sharma	isha.sharma34@company.com	HR	CC108	G5	2022-11-29	t	t	E1123	E
E1035	Aarav	Reddy	aarav.reddy35@company.com	Sales	CC109	G1	2022-12-30	t	t	E1029	E
E1036	Ananya	Verma	ananya.verma36@company.com	Operations	CC109	G1	2024-05-14	t	t	E1184	E
E1037	Ananya	Agarwal	ananya.agarwal37@company.com	Finance	CC104	G2	2024-05-09	t	f	E1004	E
E1038	Vihaan	Kumar	vihaan.kumar38@company.com	Finance	CC107	G3	2023-11-18	t	t	E1051	E
E1039	Aarav	Nair	aarav.nair39@company.com	Sales	CC101	G5	2024-07-06	t	t	E1090	E
E1040	Kavya	Kumar	kavya.kumar40@company.com	Sales	CC103	G3	2023-02-21	t	f	E1051	E
E1041	Aditya	Nair	aditya.nair41@company.com	Operations	CC108	G1	2024-04-17	t	f	E1105	E
E1042	Vivaan	Patel	vivaan.patel42@company.com	Sales	CC108	G2	2023-07-06	t	f	E1122	E
E1043	Arjun	Agarwal	arjun.agarwal43@company.com	Engineering	CC104	G5	2023-05-12	t	f	E1078	E
E1044	Arjun	Sharma	arjun.sharma44@company.com	HR	CC104	G1	2023-01-11	t	t	E1184	E
E1045	Isha	Patel	isha.patel45@company.com	Engineering	CC107	G5	2024-07-22	t	f	E1251	E
E1046	Kavya	Sharma	kavya.sharma46@company.com	Engineering	CC108	G1	2023-01-31	t	f	E1242	E
E1047	Diya	Reddy	diya.reddy47@company.com	Engineering	CC100	G3	2023-03-09	t	f	E1167	E
E1048	Aarav	Singh	aarav.singh48@company.com	Sales	CC105	G5	2023-05-12	t	f	E1299	E
E1049	Diya	Patel	diya.patel49@company.com	Engineering	CC106	G1	2023-06-08	t	t	E1073	E
E1050	Isha	Mehta	isha.mehta50@company.com	Finance	CC102	G1	2024-08-24	t	f	E1185	E
E1052	Vihaan	Sharma	vihaan.sharma52@company.com	HR	CC105	G3	2024-08-14	t	t	E1297	E
E1053	Arjun	Singh	arjun.singh53@company.com	HR	CC108	G3	2024-07-26	t	t	E1217	E
E1054	Vivaan	Kumar	vivaan.kumar54@company.com	Finance	CC100	G1	2023-04-09	t	f	E1123	E
E1055	Isha	Singh	isha.singh55@company.com	Operations	CC101	G4	2023-12-29	t	t	E1078	E
E1056	Arjun	Sharma	arjun.sharma56@company.com	Sales	CC108	G5	2024-10-03	t	t	E1058	E
E1057	Isha	Mehta	isha.mehta57@company.com	Operations	CC105	G1	2022-12-19	t	f	E1106	E
E1060	Ananya	Reddy	ananya.reddy60@company.com	Finance	CC103	G4	2022-10-09	t	f	E1185	E
E1061	Saanvi	Nair	saanvi.nair61@company.com	Operations	CC107	G2	2024-01-04	t	t	E1293	E
E1062	Arjun	Reddy	arjun.reddy62@company.com	Operations	CC105	G1	2024-08-18	t	t	E1080	E
E1063	Arjun	Gupta	arjun.gupta63@company.com	Sales	CC100	G2	2023-04-30	t	f	E1004	E
E1064	Diya	Verma	diya.verma64@company.com	Operations	CC103	G4	2024-01-18	t	f	E1213	E
E1065	Ananya	Gupta	ananya.gupta65@company.com	Sales	CC101	G4	2023-03-09	t	t	E1078	E
E1066	Aditya	Reddy	aditya.reddy66@company.com	Operations	CC103	G1	2024-01-27	t	f	E1185	E
E1067	Aditya	Nair	aditya.nair67@company.com	Operations	CC109	G3	2024-08-22	t	f	E1018	E
E1068	Diya	Reddy	diya.reddy68@company.com	HR	CC102	G4	2023-12-19	t	f	E1293	E
E1069	Arjun	Gupta	arjun.gupta69@company.com	Operations	CC107	G2	2024-07-22	t	f	E1122	E
E1071	Kavya	Verma	kavya.verma71@company.com	Engineering	CC106	G2	2023-02-27	t	t	E1058	E
E1072	Vivaan	Mehta	vivaan.mehta72@company.com	Operations	CC107	G4	2023-11-30	t	t	E1213	E
E1074	Aarav	Singh	aarav.singh74@company.com	HR	CC108	G5	2023-08-10	t	t	E1229	E
E1075	Saanvi	Gupta	saanvi.gupta75@company.com	HR	CC100	G4	2023-07-15	t	f	E1220	E
E1076	Ananya	Patel	ananya.patel76@company.com	Operations	CC108	G1	2024-01-30	t	f	E1122	E
E1093	Saanvi	Sharma	saanvi.sharma93@company.com	Engineering	CC106	G2	2023-01-12	t	f	E1088	E
E1094	Diya	Singh	diya.singh94@company.com	Operations	CC105	G4	2024-02-05	t	f	E1164	E
E1096	Isha	Verma	isha.verma96@company.com	Engineering	CC103	G4	2024-04-09	t	f	E1221	E
E1097	Diya	Reddy	diya.reddy97@company.com	Sales	CC103	G3	2024-06-11	t	t	E1004	E
E1098	Isha	Patel	isha.patel98@company.com	Operations	CC102	G3	2023-08-14	t	t	E1090	E
E1099	Aarav	Reddy	aarav.reddy99@company.com	HR	CC101	G1	2023-08-04	t	f	E1088	E
E1100	Saanvi	Nair	saanvi.nair100@company.com	Engineering	CC100	G3	2024-01-03	t	f	E1248	E
E1101	Vivaan	Verma	vivaan.verma101@company.com	Sales	CC109	G1	2023-11-23	t	t	E1213	E
E1102	Aditya	Agarwal	aditya.agarwal102@company.com	Engineering	CC101	G5	2023-08-16	t	f	E1251	E
E1103	Diya	Agarwal	diya.agarwal103@company.com	Operations	CC106	G4	2024-07-03	t	f	E1228	E
E1104	Arjun	Agarwal	arjun.agarwal104@company.com	Operations	CC109	G1	2023-12-22	t	t	E1191	E
E1107	Vihaan	Kumar	vihaan.kumar107@company.com	HR	CC101	G2	2024-10-01	t	f	E1027	E
E1108	Diya	Gupta	diya.gupta108@company.com	Operations	CC103	G2	2023-12-18	t	f	E1070	E
E1109	Aditya	Verma	aditya.verma109@company.com	Finance	CC109	G5	2022-12-09	t	f	E1297	E
E1111	Saanvi	Verma	saanvi.verma111@company.com	HR	CC105	G5	2024-06-12	t	f	E1242	E
E1112	Aarav	Verma	aarav.verma112@company.com	Operations	CC100	G3	2023-05-31	t	t	E1029	E
E1113	Aditya	Nair	aditya.nair113@company.com	HR	CC104	G2	2024-03-23	t	f	E1105	E
E1114	Saanvi	Verma	saanvi.verma114@company.com	HR	CC105	G3	2024-02-02	t	t	E1147	E
E1115	Aditya	Singh	aditya.singh115@company.com	Finance	CC106	G5	2023-12-04	t	t	E1051	E
E1116	Saanvi	Verma	saanvi.verma116@company.com	Finance	CC101	G4	2023-08-27	t	t	E1139	E
E1117	Kavya	Nair	kavya.nair117@company.com	Engineering	CC108	G3	2023-12-06	t	f	E1078	E
E1118	Saanvi	Sharma	saanvi.sharma118@company.com	Operations	CC102	G3	2023-05-05	t	f	E1122	E
E1119	Saanvi	Verma	saanvi.verma119@company.com	Operations	CC103	G2	2022-11-07	t	f	E1029	E
E1120	Kavya	Sharma	kavya.sharma120@company.com	Sales	CC103	G1	2024-04-26	t	f	E1242	E
E1121	Vivaan	Patel	vivaan.patel121@company.com	Operations	CC104	G4	2024-03-02	t	f	E1184	E
E1124	Arjun	Agarwal	arjun.agarwal124@company.com	Engineering	CC107	G5	2024-05-24	t	f	E1297	E
E1125	Isha	Singh	isha.singh125@company.com	HR	CC107	G3	2024-04-26	t	t	E1297	E
E1126	Vihaan	Agarwal	vihaan.agarwal126@company.com	HR	CC100	G3	2023-11-05	t	f	E1088	E
E1128	Kavya	Agarwal	kavya.agarwal128@company.com	HR	CC101	G5	2023-09-13	t	f	E1275	E
E1129	Aarav	Patel	aarav.patel129@company.com	Engineering	CC101	G4	2023-12-02	t	f	E1105	E
E1130	Isha	Agarwal	isha.agarwal130@company.com	Sales	CC105	G5	2024-09-17	t	f	E1078	E
E1131	Isha	Nair	isha.nair131@company.com	Operations	CC101	G2	2024-04-15	t	f	E1011	E
E1132	Vihaan	Verma	vihaan.verma132@company.com	Sales	CC107	G2	2023-12-27	t	f	E1058	E
E1133	Aarav	Sharma	aarav.sharma133@company.com	Finance	CC105	G3	2023-09-06	t	f	E1110	E
E1134	Aditya	Gupta	aditya.gupta134@company.com	Operations	CC102	G2	2024-04-04	t	t	E1228	E
E1135	Vivaan	Agarwal	vivaan.agarwal135@company.com	Engineering	CC107	G5	2023-11-04	t	t	E1127	E
E1136	Vihaan	Nair	vihaan.nair136@company.com	HR	CC104	G1	2024-07-23	t	f	E1293	E
E1137	Arjun	Reddy	arjun.reddy137@company.com	HR	CC105	G5	2023-03-19	t	f	E1012	E
E1138	Ananya	Kumar	ananya.kumar138@company.com	Engineering	CC106	G4	2024-01-19	t	t	E1127	E
E1140	Ananya	Kumar	ananya.kumar140@company.com	Sales	CC109	G4	2022-10-17	t	f	E1299	E
E1141	Vihaan	Agarwal	vihaan.agarwal141@company.com	Engineering	CC109	G3	2023-10-04	t	t	E1213	E
E1142	Vivaan	Sharma	vivaan.sharma142@company.com	Sales	CC109	G3	2023-08-21	t	t	E1167	E
E1143	Vivaan	Kumar	vivaan.kumar143@company.com	Engineering	CC103	G2	2023-09-08	t	f	E1105	E
E1144	Kavya	Reddy	kavya.reddy144@company.com	Finance	CC107	G3	2023-07-15	t	f	E1004	E
E1145	Vivaan	Nair	vivaan.nair145@company.com	Engineering	CC106	G5	2022-12-25	t	f	E1080	E
E1146	Vivaan	Mehta	vivaan.mehta146@company.com	Operations	CC101	G4	2022-10-23	t	f	E1080	E
E1148	Aarav	Agarwal	aarav.agarwal148@company.com	Operations	CC103	G1	2024-05-05	t	f	E1106	E
E1149	Arjun	Mehta	arjun.mehta149@company.com	Sales	CC100	G3	2023-02-05	t	f	E1299	E
E1150	Vivaan	Verma	vivaan.verma150@company.com	Engineering	CC106	G4	2023-06-06	t	f	E1164	E
E1151	Kavya	Mehta	kavya.mehta151@company.com	HR	CC101	G4	2024-06-01	t	f	E1191	E
E1152	Arjun	Sharma	arjun.sharma152@company.com	Engineering	CC107	G4	2024-09-14	t	t	E1088	E
E1166	Saanvi	Mehta	saanvi.mehta166@company.com	Finance	CC106	G3	2023-12-08	t	f	E1058	E
E1168	Ananya	Verma	ananya.verma168@company.com	Operations	CC100	G5	2023-10-25	t	f	E1078	E
E1169	Vivaan	Mehta	vivaan.mehta169@company.com	Sales	CC104	G5	2023-10-06	t	f	E1088	E
E1170	Isha	Verma	isha.verma170@company.com	Engineering	CC102	G4	2024-05-22	t	t	E1027	E
E1171	Vivaan	Singh	vivaan.singh171@company.com	Sales	CC104	G5	2024-04-30	t	t	E1220	E
E1172	Ananya	Reddy	ananya.reddy172@company.com	Operations	CC100	G5	2024-07-06	t	f	E1105	E
E1173	Aarav	Patel	aarav.patel173@company.com	Finance	CC105	G1	2023-07-15	t	t	E1184	E
E1174	Aditya	Agarwal	aditya.agarwal174@company.com	Sales	CC102	G1	2024-08-12	t	t	E1051	E
E1175	Kavya	Gupta	kavya.gupta175@company.com	HR	CC105	G2	2023-10-29	t	f	E1228	E
E1177	Diya	Sharma	diya.sharma177@company.com	Finance	CC107	G4	2024-08-29	t	f	E1029	E
E1178	Diya	Nair	diya.nair178@company.com	Engineering	CC108	G1	2023-12-07	t	f	E1011	E
E1179	Ananya	Verma	ananya.verma179@company.com	HR	CC108	G3	2023-07-26	t	t	E1012	E
E1180	Vihaan	Mehta	vihaan.mehta180@company.com	Sales	CC103	G3	2024-06-13	t	t	E1229	E
E1181	Aditya	Kumar	aditya.kumar181@company.com	Sales	CC100	G4	2023-08-01	t	f	E1248	E
E1182	Aditya	Patel	aditya.patel182@company.com	Engineering	CC108	G5	2023-11-02	t	f	E1184	E
E1183	Vivaan	Mehta	vivaan.mehta183@company.com	Sales	CC107	G1	2022-11-21	t	f	E1176	E
E1186	Vivaan	Gupta	vivaan.gupta186@company.com	HR	CC108	G1	2023-12-29	t	f	E1058	E
E1187	Arjun	Singh	arjun.singh187@company.com	Engineering	CC101	G5	2023-05-23	t	t	E1012	E
E1188	Kavya	Reddy	kavya.reddy188@company.com	Finance	CC102	G2	2023-04-25	t	t	E1027	E
E1190	Saanvi	Nair	saanvi.nair190@company.com	HR	CC109	G5	2024-05-08	t	f	E1185	E
E1192	Diya	Sharma	diya.sharma192@company.com	Sales	CC104	G4	2023-10-04	t	f	E1122	E
E1193	Aarav	Sharma	aarav.sharma193@company.com	Sales	CC101	G5	2023-10-21	t	f	E1242	E
E1194	Saanvi	Agarwal	saanvi.agarwal194@company.com	HR	CC109	G2	2024-04-28	t	f	E1123	E
E1195	Diya	Nair	diya.nair195@company.com	Sales	CC107	G1	2024-03-05	t	f	E1011	E
E1196	Vivaan	Reddy	vivaan.reddy196@company.com	Sales	CC103	G4	2024-07-31	t	f	E1088	E
E1197	Kavya	Reddy	kavya.reddy197@company.com	Finance	CC105	G3	2024-06-24	t	f	E1164	E
E1198	Ananya	Singh	ananya.singh198@company.com	Sales	CC105	G1	2024-09-03	t	f	E1164	E
E1199	Vivaan	Reddy	vivaan.reddy199@company.com	Finance	CC104	G5	2024-09-02	t	t	E1297	E
E1200	Isha	Verma	isha.verma200@company.com	Finance	CC104	G4	2024-05-27	t	t	E1220	E
E1201	Diya	Verma	diya.verma201@company.com	HR	CC105	G2	2023-08-22	t	t	E1242	E
E1202	Ananya	Reddy	ananya.reddy202@company.com	Finance	CC104	G2	2023-10-14	t	t	E1299	E
E1203	Isha	Nair	isha.nair203@company.com	Engineering	CC102	G1	2023-04-23	t	f	E1110	E
E1204	Vivaan	Reddy	vivaan.reddy204@company.com	Sales	CC105	G5	2024-04-13	t	t	E1122	E
E1205	Diya	Mehta	diya.mehta205@company.com	Engineering	CC109	G2	2023-03-15	t	f	E1105	E
E1206	Aarav	Mehta	aarav.mehta206@company.com	HR	CC109	G3	2023-10-17	t	f	E1095	E
E1207	Vihaan	Reddy	vihaan.reddy207@company.com	HR	CC103	G3	2023-06-10	t	f	E1078	E
E1208	Saanvi	Kumar	saanvi.kumar208@company.com	Operations	CC106	G2	2023-11-04	t	t	E1248	E
E1209	Diya	Patel	diya.patel209@company.com	HR	CC105	G5	2023-06-22	t	t	E1088	E
E1210	Kavya	Verma	kavya.verma210@company.com	Engineering	CC104	G4	2023-07-27	t	t	E1228	E
E1211	Ananya	Verma	ananya.verma211@company.com	Finance	CC100	G4	2023-05-24	t	t	E1004	E
E1212	Ananya	Reddy	ananya.reddy212@company.com	HR	CC101	G3	2023-10-26	t	t	E1110	E
E1214	Arjun	Nair	arjun.nair214@company.com	HR	CC107	G5	2024-09-20	t	t	E1248	E
E1215	Vivaan	Sharma	vivaan.sharma215@company.com	Engineering	CC108	G5	2023-06-28	t	f	E1228	E
E1216	Vivaan	Kumar	vivaan.kumar216@company.com	Sales	CC100	G2	2023-06-09	t	f	E1248	E
E1218	Kavya	Agarwal	kavya.agarwal218@company.com	Finance	CC106	G1	2023-06-13	t	f	E1266	E
E1219	Vihaan	Agarwal	vihaan.agarwal219@company.com	Sales	CC108	G3	2023-12-09	t	t	E1251	E
E1222	Vihaan	Verma	vihaan.verma222@company.com	Engineering	CC100	G3	2024-05-26	t	f	E1051	E
E1223	Aditya	Nair	aditya.nair223@company.com	Engineering	CC102	G1	2024-09-20	t	f	E1248	E
E1224	Aarav	Kumar	aarav.kumar224@company.com	Engineering	CC100	G3	2023-05-03	t	f	E1147	E
E1225	Kavya	Mehta	kavya.mehta225@company.com	Finance	CC100	G2	2024-04-17	t	f	E1051	E
E1226	Isha	Sharma	isha.sharma226@company.com	Finance	CC101	G3	2024-08-10	t	f	E1228	E
E1227	Ananya	Nair	ananya.nair227@company.com	Engineering	CC107	G4	2023-11-08	t	f	E1213	E
E1238	Vihaan	Verma	vihaan.verma238@company.com	HR	CC102	G4	2023-02-24	t	t	E1106	E
E1239	Isha	Singh	isha.singh239@company.com	Operations	CC108	G3	2024-10-04	t	f	E1242	E
E1240	Aditya	Patel	aditya.patel240@company.com	Engineering	CC101	G2	2023-10-14	t	t	E1189	E
E1241	Vihaan	Nair	vihaan.nair241@company.com	Operations	CC109	G3	2022-11-04	t	f	E1058	E
E1243	Kavya	Mehta	kavya.mehta243@company.com	Sales	CC102	G3	2023-12-02	t	t	E1184	E
E1244	Saanvi	Nair	saanvi.nair244@company.com	Finance	CC102	G5	2024-09-04	t	t	E1012	E
E1245	Aditya	Mehta	aditya.mehta245@company.com	Sales	CC108	G2	2024-03-06	t	f	E1213	E
E1246	Aditya	Patel	aditya.patel246@company.com	Finance	CC108	G3	2023-09-04	t	t	E1217	E
E1247	Arjun	Gupta	arjun.gupta247@company.com	Finance	CC102	G3	2024-07-20	t	t	E1221	E
E1249	Diya	Sharma	diya.sharma249@company.com	Sales	CC109	G3	2022-11-07	t	t	E1217	E
E1250	Diya	Mehta	diya.mehta250@company.com	Sales	CC107	G5	2024-07-02	t	f	E1139	E
E1252	Aditya	Nair	aditya.nair252@company.com	HR	CC103	G3	2023-12-08	t	t	E1248	E
E1253	Isha	Singh	isha.singh253@company.com	Engineering	CC105	G5	2023-09-27	t	t	E1123	E
E1254	Isha	Gupta	isha.gupta254@company.com	Finance	CC107	G2	2024-01-29	t	t	E1189	E
E1255	Vivaan	Sharma	vivaan.sharma255@company.com	Operations	CC106	G2	2023-08-02	t	t	E1051	E
E1256	Isha	Agarwal	isha.agarwal256@company.com	Engineering	CC107	G5	2023-08-25	t	f	E1088	E
E1257	Saanvi	Kumar	saanvi.kumar257@company.com	Sales	CC106	G5	2024-03-01	t	f	E1297	E
E1258	Vihaan	Gupta	vihaan.gupta258@company.com	Sales	CC100	G3	2024-05-28	t	f	E1189	E
E1259	Diya	Nair	diya.nair259@company.com	Sales	CC101	G4	2023-07-28	t	t	E1123	E
E1260	Arjun	Singh	arjun.singh260@company.com	Sales	CC106	G1	2023-11-25	t	t	E1059	E
E1261	Isha	Reddy	isha.reddy261@company.com	HR	CC108	G4	2023-07-31	t	f	E1167	E
E1262	Diya	Agarwal	diya.agarwal262@company.com	Sales	CC106	G3	2023-02-07	t	f	E1051	E
E1263	Kavya	Singh	kavya.singh263@company.com	Operations	CC108	G4	2023-03-05	t	t	E1220	E
E1264	Aarav	Sharma	aarav.sharma264@company.com	HR	CC108	G4	2023-02-26	t	t	E1123	E
E1265	Diya	Reddy	diya.reddy265@company.com	Operations	CC105	G2	2023-03-01	t	f	E1229	E
E1267	Diya	Kumar	diya.kumar267@company.com	Finance	CC105	G1	2024-02-07	t	f	E1004	E
E1268	Diya	Kumar	diya.kumar268@company.com	Sales	CC109	G4	2024-09-12	t	f	E1090	E
E1269	Diya	Agarwal	diya.agarwal269@company.com	Operations	CC107	G2	2023-05-30	t	f	E1147	E
E1270	Aditya	Gupta	aditya.gupta270@company.com	Sales	CC103	G1	2022-11-10	t	f	E1176	E
E1271	Isha	Mehta	isha.mehta271@company.com	Engineering	CC106	G5	2023-03-13	t	f	E1176	E
E1272	Aarav	Patel	aarav.patel272@company.com	Operations	CC105	G4	2024-03-23	t	f	E1059	E
E1273	Isha	Patel	isha.patel273@company.com	Finance	CC108	G3	2024-01-22	t	f	E1242	E
E1274	Diya	Nair	diya.nair274@company.com	Finance	CC108	G3	2023-04-23	t	t	E1078	E
E1276	Kavya	Kumar	kavya.kumar276@company.com	Operations	CC108	G4	2023-07-30	t	f	E1217	E
E1277	Isha	Patel	isha.patel277@company.com	Finance	CC101	G3	2023-08-02	t	f	E1059	E
E1278	Arjun	Nair	arjun.nair278@company.com	Operations	CC104	G5	2023-05-16	t	f	E1011	E
E1279	Aditya	Verma	aditya.verma279@company.com	Engineering	CC103	G1	2024-06-30	t	t	E1251	E
E1280	Vihaan	Sharma	vihaan.sharma280@company.com	Finance	CC107	G1	2023-01-19	t	t	E1167	E
E1281	Aarav	Reddy	aarav.reddy281@company.com	HR	CC107	G2	2023-03-19	t	f	E1018	E
E1282	Isha	Kumar	isha.kumar282@company.com	Sales	CC109	G2	2024-07-31	t	t	E1127	E
E1283	Aditya	Mehta	aditya.mehta283@company.com	HR	CC107	G2	2023-04-07	t	f	E1012	E
E1284	Aarav	Sharma	aarav.sharma284@company.com	Operations	CC101	G3	2023-08-10	t	f	E1018	E
E1285	Saanvi	Reddy	saanvi.reddy285@company.com	Engineering	CC108	G4	2024-03-28	t	f	E1184	E
E1286	Vihaan	Verma	vihaan.verma286@company.com	HR	CC104	G2	2023-09-12	t	t	E1095	E
E1287	Isha	Kumar	isha.kumar287@company.com	Engineering	CC109	G4	2024-05-12	t	f	E1078	E
E1288	Kavya	Singh	kavya.singh288@company.com	Sales	CC102	G2	2023-01-05	t	f	E1070	E
E1289	Isha	Gupta	isha.gupta289@company.com	HR	CC103	G4	2022-10-15	t	f	E1122	E
E1290	Isha	Kumar	isha.kumar290@company.com	Sales	CC104	G3	2024-05-27	t	t	E1029	E
E1291	Aarav	Verma	aarav.verma291@company.com	Engineering	CC106	G5	2024-01-28	t	f	E1004	E
E1292	Vivaan	Kumar	vivaan.kumar292@company.com	Engineering	CC103	G2	2023-10-20	t	f	E1127	E
E1294	Vihaan	Agarwal	vihaan.agarwal294@company.com	HR	CC108	G3	2022-12-31	t	t	E1228	E
E1295	Diya	Verma	diya.verma295@company.com	Operations	CC103	G5	2022-12-11	t	t	E1185	E
E1296	Aditya	Singh	aditya.singh296@company.com	Sales	CC103	G5	2024-03-24	t	f	E1127	E
E1298	Saanvi	Agarwal	saanvi.agarwal298@company.com	HR	CC104	G1	2022-12-07	t	f	E1105	E
\.


--
-- Data for Name: expense_claims; Type: TABLE DATA; Schema: public; Owner: myuser
--

COPY public.expense_claims (id, claim_id, employee_id, claim_date, expense_category, amount, currency, vendor_name, linked_booking_id, receipt_id, payment_mode, status, details, others_1, others_2, auto_approved, is_duplicate, fraud_flag) FROM stdin;
129	CLM-20251028-041134	E1001	2025-03-31	travel	17061.27	INR	AirAsia (India) Private Limited	\N	AI/25983/00718	\N	Rejected	{"invoice_id": "AI/25983/00718", "employee_id": "E1001", "expense_date": "2025-03-31", "vendor": "AirAsia (India) Private Limited", "total_amount": 17061.27, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Rejected", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "AI/25983/00718", "employee_id": "E1001", "expense_date": "2025-03-31", "vendor": "AirAsia (India) Private Limited", "total_amount": 17061.27, "currency": "INR", "items": [{"description": "Air Ticket charges", "amount": 15772.64, "currency": "INR", "city": null}, {"description": "Airport Fees Pass Through", "amount": 500.0, "currency": "INR", "city": null}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "Flight", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
130	CLM-20251028-041305	E1001	2024-09-26	Hotel	11000.00	INR	agoda	\N	No2024328	\N	Rejected	{"invoice_id": "No2024328", "employee_id": "E1001", "expense_date": "2024-09-26", "vendor": "agoda", "total_amount": 11000.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Rejected", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2024328", "employee_id": "E1001", "expense_date": "2024-09-26", "vendor": "agoda", "total_amount": 11000.0, "currency": "INR", "items": [], "invoice_number": "No2024328", "date": "2024-09-26", "seller": {"hotel_name": "", "location": "Hyderabad, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
131	CLM-20251028-174028	E1018	2024-11-29	Hotel	7542.00	INR	Sunshine Hotel Hotel	\N	No2024149	\N	Auto Approved	{"invoice_id": "No2024149", "employee_id": "E1018", "expense_date": "2024-11-29", "vendor": "Sunshine Hotel Hotel", "total_amount": 7542.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2024149", "employee_id": "E1018", "expense_date": "2024-11-29", "vendor": "Sunshine Hotel Hotel", "total_amount": 7542.0, "currency": "INR", "items": [], "invoice_number": "No2024149", "date": "2024-11-29", "seller": {"hotel_name": "", "location": "Area 7, Hyderabad, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
133	CLM-20251028-174219	E1032	2024-05-30	travel	10000.00	INR	Omicron Systems	\N	272868001879	\N	Rejected	{"invoice_id": "272868001879", "employee_id": "E1032", "expense_date": "2024-05-30", "vendor": "Omicron Systems", "total_amount": 10000.0, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Rejected", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "272868001879", "employee_id": "E1032", "expense_date": "2024-05-30", "vendor": "Omicron Systems", "total_amount": 10000.0, "currency": "INR", "items": [{"description": "Base Fare", "amount": 8850.18, "currency": "INR", "city": "Noida"}, {"description": "Airline Fuel Charge", "amount": 619.51, "currency": "INR", "city": "Noida"}, {"description": "CUTE Charge", "amount": 204.19, "currency": "INR", "city": "Noida"}, {"description": "Other Charges", "amount": 203.78, "currency": "INR", "city": "Noida"}, {"description": "Passenger Service Fee", "amount": 228.54, "currency": "INR", "city": "Noida"}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
135	CLM-20251028-174457	E1004	2024-03-25	travel	34521.51	INR	AirAsia (India) Private Limited	\N	AI/24585/00145	\N	Rejected	{"invoice_id": "AI/24585/00145", "employee_id": "E1004", "expense_date": "2024-03-25", "vendor": "AirAsia (India) Private Limited", "total_amount": 34521.51, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Rejected", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "AI/24585/00145", "employee_id": "E1004", "expense_date": "2024-03-25", "vendor": "AirAsia (India) Private Limited", "total_amount": 34521.51, "currency": "INR", "items": [{"description": "Air Ticket charges", "amount": 32401.44, "currency": "INR", "city": null}, {"description": "Airport Fees Pass Through", "amount": 500.0, "currency": "INR", "city": null}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
136	CLM-20251028-174543	E1004	2024-05-18	travel	10820.80	INR	AirAsia (India) Private Limited	\N	AI/24712/00466	\N	Rejected	{"invoice_id": "AI/24712/00466", "employee_id": "E1004", "expense_date": "2024-05-18", "vendor": "AirAsia (India) Private Limited", "total_amount": 10820.8, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Rejected", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "AI/24712/00466", "employee_id": "E1004", "expense_date": "2024-05-18", "vendor": "AirAsia (India) Private Limited", "total_amount": 10820.8, "currency": "INR", "items": [{"description": "Air Ticket charges", "amount": 10320.8, "currency": "INR", "city": null}, {"description": "Airport Fees Pass Through", "amount": 500.0, "currency": "INR", "city": null}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
138	CLM-20251028-174725	E1025	2024-09-08	travel	244.47	INR	Ola	\N	1731537896	\N	Auto Approved	{"invoice_id": "1731537896", "employee_id": "E1025", "expense_date": "2024-09-08", "vendor": "Ola", "total_amount": 244.47, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "1731537896", "employee_id": "E1025", "expense_date": "2024-09-08", "vendor": "Ola", "total_amount": 244.47, "currency": "INR", "items": [{"description": "Base Fare", "amount": 30.63, "currency": "INR", "city": "Jaipur"}, {"description": "Distance Fare", "amount": 144.2, "currency": "INR", "city": "Jaipur"}, {"description": "Time Fare", "amount": 13.32, "currency": "INR", "city": "Jaipur"}, {"description": "Convenience Fee", "amount": 44.68, "currency": "INR", "city": "Jaipur"}, {"description": "GST (5%)", "amount": 11.64, "currency": "INR", "city": "Jaipur"}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
140	CLM-20251028-174938	E1088	2024-02-25	Hotel	3702.00	INR	Royal Inn Inn	\N	No2024119	\N	Auto Approved	{"invoice_id": "No2024119", "employee_id": "E1088", "expense_date": "2024-02-25", "vendor": "Royal Inn Inn", "total_amount": 3702.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2024119", "employee_id": "E1088", "expense_date": "2024-02-25", "vendor": "Royal Inn Inn", "total_amount": 3702.0, "currency": "INR", "items": [{"description": "Accommodation", "amount": 3702.0, "currency": "INR", "city": "Hyderabad"}], "invoice_number": "No2024119", "date": "2024-02-25", "seller": {"hotel_name": "", "location": "Area 2, Hyderabad, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
132	CLM-20251028-174132	E1115	2025-09-20	Hotel	4170.00	INR	Crystal Hotel Suites	\N	No2024373	\N	Auto Approved	{"invoice_id": "No2024373", "employee_id": "E1115", "expense_date": "2025-09-20", "vendor": "Crystal Hotel Suites", "total_amount": 4170.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2024373", "employee_id": "E1115", "expense_date": "2025-09-20", "vendor": "Crystal Hotel Suites", "total_amount": 4170.0, "currency": "INR", "items": [], "invoice_number": "No2024373", "date": "2025-09-20", "seller": {"hotel_name": "", "location": "Block 27, New Delhi, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
134	CLM-20251028-174403	E1020	2025-09-08	travel	52291.94	INR	AirAsia (India) Private Limited	\N	AI/25554/00797	\N	Rejected	{"invoice_id": "AI/25554/00797", "employee_id": "E1020", "expense_date": "2025-09-08", "vendor": "AirAsia (India) Private Limited", "total_amount": 52291.94, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Rejected", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "AI/25554/00797", "employee_id": "E1020", "expense_date": "2025-09-08", "vendor": "AirAsia (India) Private Limited", "total_amount": 52291.94, "currency": "INR", "items": [{"description": "Air Ticket charges", "amount": 49325.66, "currency": "INR", "city": null}, {"description": "Airport Fees Pass Through", "amount": 500.0, "currency": "INR", "city": null}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
137	CLM-20251028-174643	E1025	2024-03-12	Hotel	3856.00	INR	Sunshine Hotel Inn	\N	No2024755	\N	Auto Approved	{"invoice_id": "No2024755", "employee_id": "E1025", "expense_date": "2024-03-12", "vendor": "Sunshine Hotel Inn", "total_amount": 3856.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2024755", "employee_id": "E1025", "expense_date": "2024-03-12", "vendor": "Sunshine Hotel Inn", "total_amount": 3856.0, "currency": "INR", "items": [{"description": "Accommodation", "amount": 3856.0, "currency": "INR", "city": "Noida"}], "invoice_number": "No2024755", "date": "2024-03-12", "seller": {"hotel_name": "", "location": "Road 24, Noida, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
139	CLM-20251028-174815	E1025	2024-08-28	travel	318.32	INR	Ola	\N	8335413012	\N	Auto Approved	{"invoice_id": "8335413012", "employee_id": "E1025", "expense_date": "2024-08-28", "vendor": "Ola", "total_amount": 318.32, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "8335413012", "employee_id": "E1025", "expense_date": "2024-08-28", "vendor": "Ola", "total_amount": 318.32, "currency": "INR", "items": [{"description": "Base Fare", "amount": 41.18, "currency": "INR", "city": "Pune"}, {"description": "Distance Fare", "amount": 112.97, "currency": "INR", "city": "Pune"}, {"description": "Time Fare", "amount": 128.46, "currency": "INR", "city": "Pune"}, {"description": "Convenience Fee", "amount": 20.55, "currency": "INR", "city": "Pune"}, {"description": "GST (5%)", "amount": 15.16, "currency": "INR", "city": "Pune"}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
141	CLM-20251028-175028	E1111	2024-09-26	Hotel	2121.00	INR	Emerald Retreat Hotel	\N	No2024328	\N	Auto Approved	{"invoice_id": "No2024328", "employee_id": "E1111", "expense_date": "2024-09-26", "vendor": "Emerald Retreat Hotel", "total_amount": 2121.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2024328", "employee_id": "E1111", "expense_date": "2024-09-26", "vendor": "Emerald Retreat Hotel", "total_amount": 2121.0, "currency": "INR", "items": [], "invoice_number": "No2024328", "date": "2024-09-26", "seller": {"hotel_name": "", "location": "Road 42, Hyderabad, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
142	CLM-20251028-175150	E1012	2024-08-02	Hotel	7676.00	INR	Paradise Suites	\N	No2025750	\N	Auto Approved	{"invoice_id": "No2025750", "employee_id": "E1012", "expense_date": "2024-08-02", "vendor": "Paradise Suites", "total_amount": 7676.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2025750", "employee_id": "E1012", "expense_date": "2024-08-02", "vendor": "Paradise Suites", "total_amount": 7676.0, "currency": "INR", "items": [], "invoice_number": "No2025750", "date": "2024-08-02", "seller": {"hotel_name": "", "location": "Sector 39, Hyderabad, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
126	CLM-20251028-040421	E1001	2024-09-26	Hotel	4500.00	INR	Emerald Retreat Hotel	\N	No2024328	\N	Auto Approved	{"invoice_id": "No2024328", "employee_id": "E1001", "expense_date": "2024-09-26", "vendor": "Emerald Retreat Hotel", "total_amount": 4500.0, "currency": "INR", "category": "Hotel", "travel_block": null, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Auto Approved", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "No2024328", "employee_id": "E1001", "expense_date": "2024-09-26", "vendor": "Emerald Retreat Hotel", "total_amount": 4500.0, "currency": "INR", "items": [{"description": "Accommodation", "amount": 4500.0, "currency": "INR", "city": "Hyderabad"}], "invoice_number": "No2024328", "date": "2024-09-26", "seller": {"hotel_name": "", "location": "Road 42, Hyderabad, India"}, "buyer": {"name": "", "email": ""}, "booking_details": {"booking_number": "", "payment_reference": "", "check_in": "2025-10-28", "check_out": "2025-10-28"}, "total": 0.0, "category": "Hotel"}	\N	f	f	f
127	CLM-20251028-040611	E1004	2025-05-25	travel	3500.00	INR	Ola	\N	038704629	\N	Approved	{"invoice_id": "038704629", "employee_id": "E1004", "expense_date": "2025-05-25", "vendor": "Ola", "total_amount": 3500.0, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Pending", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "038704629", "employee_id": "E1004", "expense_date": "2025-05-25", "vendor": "Ola", "total_amount": 3500.0, "currency": "INR", "items": [{"description": "Base Fare", "amount": 33.53, "currency": "INR", "city": "Chennai"}, {"description": "Distance Fare", "amount": 107.5, "currency": "INR", "city": "Chennai"}, {"description": "Time Fare", "amount": 25.66, "currency": "INR", "city": "Chennai"}, {"description": "Convenience Fee", "amount": 24.24, "currency": "INR", "city": "Chennai"}, {"description": "GST (5%)", "amount": 9.55, "currency": "INR", "city": "Chennai"}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "Cab", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
128	CLM-20251028-040832	E1037	2025-05-25	travel	10000.00	INR	Ola	\N	038704462	\N	Approved	{"invoice_id": "038704462", "employee_id": "E1037", "expense_date": "2025-05-25", "vendor": "Ola", "total_amount": 10000.0, "currency": "INR", "category": "travel", "travel_block": null, "booking_details": null, "food_details": null, "other_details": null, "payment_mode": null, "status_from_tag": "Finance Pending", "auto_approved_from_tag": false, "raw_tag": ""}	{"invoice_id": "038704462", "employee_id": "E1037", "expense_date": "2025-05-25", "vendor": "Ola", "total_amount": 10000.0, "currency": "INR", "items": [{"description": "Base Fare", "amount": 33.53, "currency": "INR", "city": "Chennai"}, {"description": "Distance Fare", "amount": 107.5, "currency": "INR", "city": "Chennai"}, {"description": "Time Fare", "amount": 25.66, "currency": "INR", "city": "Chennai"}, {"description": "Convenience Fee", "amount": 9627.31, "currency": "INR", "city": "Chennai"}, {"description": "GST (5%)", "amount": 476.0, "currency": "INR", "city": "Chennai"}], "travel_details": {"from_city": "", "to_city": "", "travel_mode": "Cab", "travel_date": "2025-10-28"}, "category": "travel"}	\N	f	f	f
\.


--
-- Data for Name: expense_policies; Type: TABLE DATA; Schema: public; Owner: myuser
--

COPY public.expense_policies (id, policy_id, category, max_allowance, per_diem, applicable_grades, notes) FROM stdin;
2	P401	Travel	9903.70	825.82	G5, G1	Policy for Office Supplies
3	P402	Other	13731.91	1578.74	G4, G3	Policy for Other
4	P403	Other	1347.05	1824.54	G2, G4	Policy for Other
5	P404	Other	15489.10	1376.29	G5, G2	Policy for Other
6	P405	Local Conveyance	3110.72	1692.85	G2, G1	Policy for Local Conveyance
7	P406	Lodging	12166.70	1859.33	G3, G2	Policy for Local Conveyance
8	P407	Travel	14328.40	2473.56	G5, G1	Policy for Travel
9	P408	Travel	3200.00	1500.00	G3, G4,G5	Policy for business travel expenses
1	P400	Office Supplies	8000.00	2459.67	G5, G1	Policy for Office Supplies
10	P409	Travel	8000.00	1500.00	G2	Policy for business travel expenses
11	P410	hotel	5000.00	0.00	G1,G2,G3	Max allowance for hotel stays for Grade G1, G2, and G3.
12	P411	hotel	10000.00	0.00	G4,G5	Max allowance for hotel stays for Grade G4 and G5.
13	P413	food	1000.00	75.00	G1, G2, G3	Standard daily meal allowance
14	P414	food	1100.00	120.00	G4, G5	Executive meal allowance (client meetings)
\.


--
-- Data for Name: expense_validation_logs; Type: TABLE DATA; Schema: public; Owner: myuser
--

COPY public.expense_validation_logs (log_id, claim_id, employee_id, status_val, payment_mode, auto_approved, raw_validation_json, created_at) FROM stdin;
1	CLM-20251025-183720	E1004	ValidationError	\N	f	{"status": "ValidationError", "error_msg": "module 'agent' has no attribute 'run_validation_agent'", "payment_mode": null, "auto_approved": false}	2025-10-25 13:07:20.539581
2	CLM-20251025-184308	E1004	Pending Review	\N	f	{"tag": "Auto Approved", "comments": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "decision": "Approved", "validation": {"tag": "Auto Approved", "message": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "metrics": {"grade": "G3", "category": "travel", "currency": "INR", "percent_diff": 0.0, "spent_amount": 1000.0, "allowed_amount": 3200.0}, "decision": "Approved", "rule_band": "within_limit", "manager_id": "E1106"}}	2025-10-25 13:13:11.088185
3	CLM-20251025-184628	E1004	Pending Review	\N	f	{"tag": "Auto Approved", "comments": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "decision": "Approved", "validation": {"tag": "Auto Approved", "message": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "metrics": {"grade": "G3", "category": "travel", "currency": "INR", "percent_diff": 0.0, "spent_amount": 1000.0, "allowed_amount": 3200.0}, "decision": "Approved", "rule_band": "within_limit", "manager_id": "E1106"}}	2025-10-25 13:16:28.773722
4	CLM-20251025-190041	E1004	Pending Review	\N	f	{"tag": "Auto Approved", "comments": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "decision": "Approved", "validation": {"tag": "Auto Approved", "message": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "metrics": {"grade": "G3", "category": "travel", "currency": "INR", "percent_diff": 0.0, "spent_amount": 1000.0, "allowed_amount": 3200.0}, "decision": "Approved", "rule_band": "within_limit", "manager_id": "E1106"}}	2025-10-25 13:30:41.635412
5	CLM-20251025-190944	E1004	Pending Review	\N	f	{"tag": "Auto Approved", "comments": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "decision": "Approved", "validation": {"tag": "Auto Approved", "message": "Isha Verma (Grade G3) submitted a travel expense of INR 1000.00. Policy allows up to INR 3200.00. This is within the allowed limit, so it is auto approved.", "metrics": {"grade": "G3", "category": "travel", "currency": "INR", "percent_diff": 0.0, "spent_amount": 1000.0, "allowed_amount": 3200.0}, "decision": "Approved", "rule_band": "within_limit", "manager_id": "E1106"}}	2025-10-25 13:39:44.609897
6	CLM-20251027-194136	E1037	Pending Review	\N	f	{"tag": "Finance Pending", "comments": "Ananya Agarwal (Grade G2) submitted a travel expense of INR 9600.00. Policy allows up to INR 8000.00. Exceeds the policy limit by 10%–25%. Finance review.", "decision": "Send to Finance Team", "validation": {"tag": "Finance Pending", "message": "Ananya Agarwal (Grade G2) submitted a travel expense of INR 9600.00. Policy allows up to INR 8000.00. Exceeds the policy limit by 10%–25%. Finance review.", "metrics": {"grade": "G2", "category": "travel", "currency": "INR", "percent_diff": 20.0, "spent_amount": 9600.0, "allowed_amount": 8000.0}, "decision": "Send to Finance Team", "rule_band": "over_by_10_to_25", "manager_id": "E1004"}}	2025-10-27 14:11:36.490284
7	CLM-20251027-194436	E1004	Pending Review	\N	f	{"tag": "Pending", "comments": "Isha Verma (Grade G3) submitted a travel expense of INR 3500.00. Policy allows up to INR 3200.00. Exceeds the policy limit by up to 10%. Send to manager.", "decision": "Send to Manager", "validation": {"tag": "Pending", "message": "Isha Verma (Grade G3) submitted a travel expense of INR 3500.00. Policy allows up to INR 3200.00. Exceeds the policy limit by up to 10%. Send to manager.", "metrics": {"grade": "G3", "category": "travel", "currency": "INR", "percent_diff": 9.38, "spent_amount": 3500.0, "allowed_amount": 3200.0}, "decision": "Send to Manager", "rule_band": "over_by_0_to_10", "manager_id": "E1106"}}	2025-10-27 14:14:36.803747
8	CLM-20251027-194652	E1037	Pending Review	\N	f	{"tag": "Finance Pending", "comments": "Ananya Agarwal (Grade G2) submitted a travel expense of INR 10000.00. Policy allows up to INR 8000.00. Exceeds the policy limit by 10%–25%. Finance review.", "decision": "Send to Finance Team", "validation": {"tag": "Finance Pending", "message": "Ananya Agarwal (Grade G2) submitted a travel expense of INR 10000.00. Policy allows up to INR 8000.00. Exceeds the policy limit by 10%–25%. Finance review.", "metrics": {"grade": "G2", "category": "travel", "currency": "INR", "percent_diff": 25.0, "spent_amount": 10000.0, "allowed_amount": 8000.0}, "decision": "Send to Finance Team", "rule_band": "over_by_10_to_25", "manager_id": "E1004"}}	2025-10-27 14:16:52.715578
\.


--
-- Data for Name: per_diem_rates; Type: TABLE DATA; Schema: public; Owner: myuser
--

COPY public.per_diem_rates (id, location, currency, per_diem_rate, created_at) FROM stdin;
1	Mumbai	INR	1500.00	2025-10-17 20:38:50.866803
2	Bengaluru	INR	1200.00	2025-10-17 20:38:50.866803
3	London	GBP	120.00	2025-10-17 20:38:50.866803
4	San Francisco	USD	160.00	2025-10-17 20:38:50.866803
\.


--
-- Data for Name: reimbursement_accounts; Type: TABLE DATA; Schema: public; Owner: myuser
--

COPY public.reimbursement_accounts (id, bank_account_id, employee_id, bank_name, account_number_masked, ifsc) FROM stdin;
\.


--
-- Data for Name: vendors; Type: TABLE DATA; Schema: public; Owner: myuser
--

COPY public.vendors (id, vendor_id, vendor_name, category, country, contract_rate_reference, vendor_verified) FROM stdin;
\.


--
-- Name: expense_claims_id_seq; Type: SEQUENCE SET; Schema: public; Owner: myuser
--

SELECT pg_catalog.setval('public.expense_claims_id_seq', 142, true);


--
-- Name: expense_policies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: myuser
--

SELECT pg_catalog.setval('public.expense_policies_id_seq', 10, true);


--
-- Name: expense_validation_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: myuser
--

SELECT pg_catalog.setval('public.expense_validation_logs_log_id_seq', 8, true);


--
-- Name: per_diem_rates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: myuser
--

SELECT pg_catalog.setval('public.per_diem_rates_id_seq', 4, true);


--
-- Name: reimbursement_accounts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: myuser
--

SELECT pg_catalog.setval('public.reimbursement_accounts_id_seq', 1, false);


--
-- Name: vendors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: myuser
--

SELECT pg_catalog.setval('public.vendors_id_seq', 1, false);


--
-- Name: employees employees_email_key; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_email_key UNIQUE (email);


--
-- Name: employees employees_pkey; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (employee_id);


--
-- Name: expense_claims expense_claims_claim_id_key; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_claims
    ADD CONSTRAINT expense_claims_claim_id_key UNIQUE (claim_id);


--
-- Name: expense_claims expense_claims_pkey; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_claims
    ADD CONSTRAINT expense_claims_pkey PRIMARY KEY (id);


--
-- Name: expense_policies expense_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_policies
    ADD CONSTRAINT expense_policies_pkey PRIMARY KEY (id);


--
-- Name: expense_validation_logs expense_validation_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_validation_logs
    ADD CONSTRAINT expense_validation_logs_pkey PRIMARY KEY (log_id);


--
-- Name: per_diem_rates per_diem_rates_pkey; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.per_diem_rates
    ADD CONSTRAINT per_diem_rates_pkey PRIMARY KEY (id);


--
-- Name: reimbursement_accounts reimbursement_accounts_bank_account_id_key; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.reimbursement_accounts
    ADD CONSTRAINT reimbursement_accounts_bank_account_id_key UNIQUE (bank_account_id);


--
-- Name: reimbursement_accounts reimbursement_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.reimbursement_accounts
    ADD CONSTRAINT reimbursement_accounts_pkey PRIMARY KEY (id);


--
-- Name: per_diem_rates uq_per_diem_location_currency; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.per_diem_rates
    ADD CONSTRAINT uq_per_diem_location_currency UNIQUE (location, currency);


--
-- Name: vendors vendors_pkey; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.vendors
    ADD CONSTRAINT vendors_pkey PRIMARY KEY (id);


--
-- Name: vendors vendors_vendor_id_key; Type: CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.vendors
    ADD CONSTRAINT vendors_vendor_id_key UNIQUE (vendor_id);


--
-- Name: idx_per_diem_currency; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX idx_per_diem_currency ON public.per_diem_rates USING btree (currency);


--
-- Name: idx_per_diem_location; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX idx_per_diem_location ON public.per_diem_rates USING btree (location);


--
-- Name: ix_category; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_category ON public.expense_policies USING btree (category);


--
-- Name: ix_claim_date; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_claim_date ON public.expense_claims USING btree (claim_date);


--
-- Name: ix_claim_employee; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_claim_employee ON public.expense_claims USING btree (employee_id);


--
-- Name: ix_claim_status; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_claim_status ON public.expense_claims USING btree (status);


--
-- Name: ix_claim_vendor; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_claim_vendor ON public.expense_claims USING btree (vendor_name);


--
-- Name: ix_employees_cost_center; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_employees_cost_center ON public.employees USING btree (cost_center);


--
-- Name: ix_employees_department; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_employees_department ON public.employees USING btree (department);


--
-- Name: ix_employees_is_active; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_employees_is_active ON public.employees USING btree (is_active);


--
-- Name: ix_employees_manager_id; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_employees_manager_id ON public.employees USING btree (manager_id);


--
-- Name: ix_policy_id; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_policy_id ON public.expense_policies USING btree (policy_id);


--
-- Name: ix_reimb_bank_name; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_reimb_bank_name ON public.reimbursement_accounts USING btree (bank_name);


--
-- Name: ix_reimb_employee_id; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_reimb_employee_id ON public.reimbursement_accounts USING btree (employee_id);


--
-- Name: ix_reimb_ifsc; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_reimb_ifsc ON public.reimbursement_accounts USING btree (ifsc);


--
-- Name: ix_vendor_category; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_vendor_category ON public.vendors USING btree (category);


--
-- Name: ix_vendor_country; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_vendor_country ON public.vendors USING btree (country);


--
-- Name: ix_vendor_name; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_vendor_name ON public.vendors USING btree (vendor_name);


--
-- Name: ix_vendor_verified; Type: INDEX; Schema: public; Owner: myuser
--

CREATE INDEX ix_vendor_verified ON public.vendors USING btree (vendor_verified);


--
-- Name: ux_expense_policies_policy_id; Type: INDEX; Schema: public; Owner: myuser
--

CREATE UNIQUE INDEX ux_expense_policies_policy_id ON public.expense_policies USING btree (policy_id);


--
-- Name: ux_per_diem_location_currency; Type: INDEX; Schema: public; Owner: myuser
--

CREATE UNIQUE INDEX ux_per_diem_location_currency ON public.per_diem_rates USING btree (location, currency);


--
-- Name: expense_claims expense_claims_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.expense_claims
    ADD CONSTRAINT expense_claims_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(employee_id);


--
-- Name: reimbursement_accounts reimbursement_accounts_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: myuser
--

ALTER TABLE ONLY public.reimbursement_accounts
    ADD CONSTRAINT reimbursement_accounts_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(employee_id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO myuser;


--
-- PostgreSQL database dump complete
--

\unrestrict 2HpOzpabsgYgHse0PdELViK9WYa0UkEFDDJ3tOt4vDasGnVCETuuZ87CNNDi7Z5

