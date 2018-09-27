CREATE OR REPLACE FUNCTION update_message() RETURNS trigger AS $$
  BEGIN
    UPDATE messages SET update_ts=now(), status=NEW.status WHERE id=NEW.message;
    return NULL;
  END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_message ON events;
CREATE TRIGGER update_message AFTER INSERT ON events FOR EACH ROW EXECUTE PROCEDURE update_message();
