<?php

declare(strict_types=1);

namespace Drupal\farm_api_oauth\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * API hook implementations for farm_api_oauth.
 */
class ApiHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_consumers_list_alter().
   *
   * Display the client_id in the list of consumers.
   */
  #[Hook('consumers_list_alter')]
  public function consumersListAlter(&$data, $context) {
    if ($context['type'] === 'header') {
      $data['client_id'] = $this->t('Client ID');
    }
    elseif ($context['type'] === 'row') {
      $entity = $context['entity'];
      $data['client_id'] = NULL;
      if ($client_id = $entity->get('client_id')->value) {
        $data['client_id'] = $client_id;
      }
    }
  }

}
