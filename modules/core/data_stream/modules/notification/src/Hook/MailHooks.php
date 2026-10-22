<?php

declare(strict_types=1);

namespace Drupal\data_stream_notification\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Mail hook implementations for data_stream_notification.
 */
class MailHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_mail().
   */
  #[Hook('mail')]
  public function mail($key, &$message, $params) {

    // Bail if not a notification email.
    if ($key !== 'notification_email') {
      return;
    }

    /** @var \Drupal\data_stream_notification\Entity\DataStreamNotification $data_stream_notification */
    $data_stream_notification = $params['data_stream_notification'];
    /** @var \Drupal\data_stream\Entity\DataStreamInterface $data_stream */
    $data_stream = $params['data_stream'];
    $url = $data_stream->toUrl()->setAbsolute()->toString();

    // Build the email subject.
    $message['subject'] = $this->t('@notification notification for data stream: @data_stream', [
      '@notification' => $data_stream_notification->label(),
      '@data_stream' => $data_stream->label(),
    ]);

    // Build the email body.
    $message['body'][] = $this->t('Data stream: <a href="@link">@label</a> Actual value: @value', [
      '@link' => $url,
      '@label' => $data_stream->label(),
      '@value' => $params['value'],
    ]);

    // Build list of condition summaries.
    $conditions = '<ul>';
    $conditions .= '<li>' . implode('</li><li>', $params['condition_summaries']) . '</li>';
    $conditions .= '</ul>';
    $message['body'][] = $conditions;
  }

}
