


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."commit_player_move"("p_room_id" "uuid", "p_player_id" "uuid", "p_new_position" "jsonb", "p_new_phase" "text", "p_new_dice_value" integer, "p_new_zone_id" "text", "p_new_config" "jsonb", "p_new_status" "text" DEFAULT 'in_progress'::"text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
    BEGIN
        -- 1. Update Player Position
        UPDATE players
        SET current_position = p_new_position
        WHERE id = p_player_id;
   
        -- 2. Update Room State
        UPDATE rooms
        SET
            phase = p_new_phase,
            dice_value = p_new_dice_value,
            current_zone_id = p_new_zone_id,
            config = p_new_config,
            status = p_new_status
        WHERE id = p_room_id;
    END;
   $$;


ALTER FUNCTION "public"."commit_player_move"("p_room_id" "uuid", "p_player_id" "uuid", "p_new_position" "jsonb", "p_new_phase" "text", "p_new_dice_value" integer, "p_new_zone_id" "text", "p_new_config" "jsonb", "p_new_status" "text") OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."cases" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "zone" integer NOT NULL,
    "description" "text" NOT NULL,
    "rubric" "jsonb" NOT NULL
);


ALTER TABLE "public"."cases" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."players" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "room_id" "uuid",
    "name" "text" NOT NULL,
    "avatar_id" "text" NOT NULL,
    "is_host" boolean DEFAULT false,
    "online_status" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "current_position" "jsonb" DEFAULT '{"edgeId": null, "nodeId": "park", "edgeProgress": 0}'::"jsonb",
    "score" integer DEFAULT 0,
    "turns_played" integer DEFAULT 0
);


ALTER TABLE "public"."players" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."rooms" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "room_code" character varying(6) NOT NULL,
    "status" "text" DEFAULT 'waiting'::"text",
    "config" "jsonb" DEFAULT '{"turns": 10, "intensity": "low"}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "dice_value" integer,
    "phase" "text" DEFAULT 'rolling'::"text",
    "current_case_id" "uuid",
    "current_zone_id" "text",
    "current_argument" "text",
    CONSTRAINT "rooms_phase_check" CHECK (("phase" = ANY (ARRAY['rolling'::"text", 'moving'::"text", 'arguing'::"text", 'voting'::"text", 'finished'::"text"]))),
    CONSTRAINT "rooms_status_check" CHECK (("status" = ANY (ARRAY['waiting'::"text", 'in_progress'::"text", 'playing'::"text", 'finished'::"text"])))
);


ALTER TABLE "public"."rooms" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."votes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "room_id" "uuid",
    "voter_name" "text" NOT NULL,
    "option_id" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."votes" OWNER TO "postgres";


ALTER TABLE ONLY "public"."cases"
    ADD CONSTRAINT "cases_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."players"
    ADD CONSTRAINT "players_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."rooms"
    ADD CONSTRAINT "rooms_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."rooms"
    ADD CONSTRAINT "rooms_room_code_key" UNIQUE ("room_code");



ALTER TABLE ONLY "public"."votes"
    ADD CONSTRAINT "votes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."votes"
    ADD CONSTRAINT "votes_room_id_voter_name_key" UNIQUE ("room_id", "voter_name");



ALTER TABLE ONLY "public"."players"
    ADD CONSTRAINT "players_room_id_fkey" FOREIGN KEY ("room_id") REFERENCES "public"."rooms"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."votes"
    ADD CONSTRAINT "votes_room_id_fkey" FOREIGN KEY ("room_id") REFERENCES "public"."rooms"("id") ON DELETE CASCADE;





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";






ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."players";



ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."rooms";



ALTER PUBLICATION "supabase_realtime" ADD TABLE ONLY "public"."votes";



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";

























































































































































GRANT ALL ON FUNCTION "public"."commit_player_move"("p_room_id" "uuid", "p_player_id" "uuid", "p_new_position" "jsonb", "p_new_phase" "text", "p_new_dice_value" integer, "p_new_zone_id" "text", "p_new_config" "jsonb", "p_new_status" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."commit_player_move"("p_room_id" "uuid", "p_player_id" "uuid", "p_new_position" "jsonb", "p_new_phase" "text", "p_new_dice_value" integer, "p_new_zone_id" "text", "p_new_config" "jsonb", "p_new_status" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."commit_player_move"("p_room_id" "uuid", "p_player_id" "uuid", "p_new_position" "jsonb", "p_new_phase" "text", "p_new_dice_value" integer, "p_new_zone_id" "text", "p_new_config" "jsonb", "p_new_status" "text") TO "service_role";


















GRANT ALL ON TABLE "public"."cases" TO "anon";
GRANT ALL ON TABLE "public"."cases" TO "authenticated";
GRANT ALL ON TABLE "public"."cases" TO "service_role";



GRANT ALL ON TABLE "public"."players" TO "anon";
GRANT ALL ON TABLE "public"."players" TO "authenticated";
GRANT ALL ON TABLE "public"."players" TO "service_role";



GRANT ALL ON TABLE "public"."rooms" TO "anon";
GRANT ALL ON TABLE "public"."rooms" TO "authenticated";
GRANT ALL ON TABLE "public"."rooms" TO "service_role";



GRANT ALL ON TABLE "public"."votes" TO "anon";
GRANT ALL ON TABLE "public"."votes" TO "authenticated";
GRANT ALL ON TABLE "public"."votes" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";































drop extension if exists "pg_net";


