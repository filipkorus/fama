interface User {
  id: number
  username: string
  public_key: string;
  is_active?: boolean;
  last_message_date?: string;
}

export default User
