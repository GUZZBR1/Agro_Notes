<?php

declare(strict_types=1);

namespace Drupal\farm_l10n\Hook;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Messenger\MessengerInterface;
use Drupal\Core\Render\Element;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\Core\Url;

/**
 * Form hook implementations for farm_l10n.
 */
class FormHooks {

  use StringTranslationTrait;

  public function __construct(
    protected ConfigFactoryInterface $configFactory,
    protected MessengerInterface $messenger,
  ) {}

  /**
   * Implements hook_form_FORM_ID_alter().
   */
  #[Hook('form_language_admin_overview_form_alter')]
  public function formLanguageAdminOverviewFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Disable the ability to change the site's default language and direct
    // users to /farm/settings/language instead.
    // @see https://www.drupal.org/project/farm/issues/3257430
    $message = $this->t('To change the default language of farmOS, please go to <a href=":url">farmOS language settings</a>.', [':url' => Url::fromRoute('farm_l10n.settings')->toString()]);
    $this->messenger->addWarning($message);
    foreach (Element::children($form['languages']) as $langcode) {
      $form['languages'][$langcode]['default']['#access'] = FALSE;
    }
  }

  /**
   * Implements hook_form_FORM_ID_alter().
   */
  #[Hook('form_user_register_form_alter')]
  public function formUserRegisterFormAlter(&$form, FormStateInterface $form_state, $form_id) {

    // Use the "Selected language" as the default for new users (unless it is
    // still set to "site_default").
    $selected_language = $this->configFactory->get('language.negotiation')->get('selected_langcode');
    if ($selected_language == 'site_default') {
      return;
    }
    if (!empty($form['language']['preferred_langcode'])) {
      $form['language']['preferred_langcode']['#default_value'] = $selected_language;
    }
    if (!empty($form['language']['preferred_admin_langcode'])) {
      $form['language']['preferred_admin_langcode']['#default_value'] = $selected_language;
    }
  }

}
