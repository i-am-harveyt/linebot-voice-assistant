import json
import logging

def convert_to_flex_message(gpt_response):
    """Convert ChatGPT's JSON response to LINE Flex Message format"""
    try:
        response_data = json.loads(gpt_response)
        response_type = response_data.get("type", "")
        
        # Create base bubble container
        flex_message = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": response_data.get("title", ""),
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "size": "lg"
                    }
                ],
                "backgroundColor": "#27AE60" if response_type == "matched" else "#F39C12" if response_type == "unmatched" else "#3498DB",
                "paddingAll": "15px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": response_data.get("message", ""),
                                "wrap": True,
                                "size": "md",
                                "margin": "md"
                            }
                        ]
                    }
                ],
                "paddingAll": "20px"
            }
        }

        # Add suggestions if available
        suggestions = response_data.get("suggestions", [])
        if suggestions:
            flex_message["body"]["contents"].append({
                "type": "separator",
                "margin": "xxl"
            })
            flex_message["body"]["contents"].append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "建議事項",
                        "weight": "bold",
                        "size": "md",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"• {suggestion}",
                                "wrap": True,
                                "size": "sm",
                                "margin": "sm"
                            } for suggestion in suggestions
                        ],
                        "margin": "md"
                    }
                ]
            })

        # Add footer
        footer_text = "建議盡快就醫檢查" if response_type == "matched" else "需要更多資訊來判斷" if response_type == "unmatched" else "請詢問健康相關問題"
        footer_color = "#2ECC71" if response_type == "matched" else "#F1C40F" if response_type == "unmatched" else "#5DADE2"
        
        flex_message["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": footer_text,
                    "color": "#FFFFFF",
                    "align": "center",
                    "size": "sm"
                }
            ],
            "backgroundColor": footer_color,
            "paddingAll": "15px"
        }

        return flex_message
    except Exception as e:
        logging.error(f"Error converting to flex message: {e}")
        return None 